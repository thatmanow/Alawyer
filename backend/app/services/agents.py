import re
import threading

from app.config import settings
from app.services.ollama_client import extract_json, ollama
from app.services.rag import rag_service

AGENT_DEFS = [
    {
        "key": "compliance",
        "name": "合规审查官",
        "focus": "合规性：对照知识库法律依据，逐条判断合同的合法性、是否违反强制性规定",
    },
    {
        "key": "risk",
        "name": "风险分析师",
        "focus": "风险水平：识别对己方不利的条款、隐含的法律风险、责任失衡点",
    },
    {
        "key": "clause",
        "name": "条款严谨性专家",
        "focus": "条款严谨性：条款表述是否清晰完整、有无歧义、必备条款是否缺失",
    },
]

VERDICT_MAP = {"compliant": "符合要求", "needs_revision": "需要修改", "non_compliant": "不符合要求"}

CONVERT_SYSTEM = "你是格式转换器。把给定的审查意见改写为严格的JSON对象，不要输出任何解释、注释或代码块标记。"
JSON_SHAPE = '{"opinion": "...", "score": 0到100整数, "points": ["要点1", "要点2"]}'


class ContractReviewOrchestrator:
    def _llm(self, system: str, user: str, timeout: int = None) -> str:
        return ollama.chat(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.4,
            timeout=timeout or settings.LLM_TIMEOUT,
        )

    def review(self, contract_text: str, contract_name: str = "") -> dict:
        chunks, meta = rag_service.retrieve(f"合同审查 {contract_name} {contract_text[:300]}", top_k=4)
        kb_context = rag_service.build_context(chunks) if chunks else "（知识库中暂无直接相关资料，请依据中国现行法律独立判断）"

        contract_brief = contract_text[:2600]

        round1 = self._run_round(contract_brief, kb_context, None)
        round2 = self._run_round(contract_brief, kb_context, round1)

        judge_report = self._judge(contract_brief, kb_context, round2, bool(chunks))

        return {
            "agents": round2,
            "kb_sources": [
                {"doc_id": c["doc_id"], "doc_name": c["doc_name"], "score": c["score"]} for c in chunks
            ],
            "verdict": judge_report.get("verdict", "needs_revision"),
            "verdict_label": VERDICT_MAP.get(judge_report.get("verdict", "needs_revision"), "需要修改"),
            "score": judge_report.get("score", 60),
            "dimensions": judge_report.get("dimensions", {}),
            "summary": judge_report.get("summary", ""),
            "optimization": judge_report.get("optimization", ""),
            "retrieval_meta": meta,
        }

    def _run_round(self, contract: str, kb: str, prev_round) -> list:
        results = [None] * len(AGENT_DEFS)

        def work(idx: int, agent: dict):
            if prev_round is None:
                user_prompt = (
                    f"待审合同《{contract[:1500]}》\n\n知识库参考：\n{kb[:1500]}\n\n"
                    f"你的审查重点：{agent['focus']}。\n"
                    "请给出你的独立审查意见。\n"
                    "只输出如下JSON（不要输出其他任何内容）：\n"
                    '{"opinion": "你的审查意见(150字以内)", "score": 0到100的整数分, "points": ["要点1", "要点2", "要点3"]}'
                )
            else:
                others = "\n\n".join(
                    f"【{prev_round[j]['name']}】意见：{prev_round[j]['opinion']}\n评分：{prev_round[j]['score']}"
                    for j in range(len(prev_round))
                    if j != idx
                )
                user_prompt = (
                    f"待审合同《{contract[:1200]}》\n\n其他专家的意见：\n{others[:1500]}\n\n"
                    f"你的审查重点：{agent['focus']}。\n"
                    "请对其他专家的意见进行反驳或补充，给出你的最终立场。\n"
                    "只输出如下JSON（不要输出其他任何内容）：\n"
                    '{"opinion": "你的最终意见(150字以内)", "score": 0到100的整数分, "points": ["要点1", "要点2", "要点3"]}'
                )
            messages = [
                {
                    "role": "system",
                    "content": f"你是{agent['name']}，一位经验丰富的法律专家，正在参与合同审查多智能体辩论。观点必须专业、具体、有法律依据。你必须只输出JSON。",
                },
                {"role": "user", "content": user_prompt},
            ]
            try:
                raw = ollama.chat(messages, temperature=0.4, json_mode=True, timeout=150)
                data = extract_json(raw)
                if not (isinstance(data, dict) and str(data.get("opinion", "")).strip()):
                    conv = ollama.chat(
                        [
                            {"role": "system", "content": CONVERT_SYSTEM},
                            {"role": "user", "content": raw[:1800] + "\n请输出：" + JSON_SHAPE},
                        ],
                        temperature=0.1,
                        json_mode=True,
                        timeout=90,
                    )
                    data = extract_json(conv)
                if isinstance(data, dict) and str(data.get("opinion", "")).strip():
                    results[idx] = self._make_result(agent, data)
                    return
                results[idx] = self._local_fallback(agent, raw)
            except Exception as e:
                results[idx] = {
                    "name": agent["name"],
                    "focus": agent["focus"],
                    "opinion": f"（本智能体暂时无法给出意见：{type(e).__name__}）",
                    "score": 60,
                    "points": [],
                }

        threads = [
            threading.Thread(target=work, args=(i, agent)) for i, agent in enumerate(AGENT_DEFS)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        return [
            r
            or {"name": a["name"], "focus": a["focus"], "opinion": "（未产出意见）", "score": 60, "points": []}
            for a, r in zip(AGENT_DEFS, results)
        ]

    @staticmethod
    def _make_result(agent: dict, data: dict) -> dict:
        try:
            score = int(float(data.get("score", 60)))
        except (TypeError, ValueError):
            score = 60
        points = [str(p).strip()[:80] for p in (data.get("points") or []) if str(p).strip()][:5]
        return {
            "name": agent["name"],
            "focus": agent["focus"],
            "opinion": str(data["opinion"]).strip()[:600],
            "score": max(0, min(100, score)),
            "points": points,
        }

    @staticmethod
    def _local_fallback(agent: dict, raw: str) -> dict:
        opinion = re.sub(r"^[#>\-\s]+", "", (raw or "").strip(), flags=re.M)[:600]
        score_m = re.search(r"[（(【\[]?(\d{1,3})\s*[分%]", raw or "")
        points = [p.strip()[:40] for p in re.findall(r"要点[一二三四五1-9]*[：:.]?\s*(.{2,40})", raw or "")][:5]
        return {
            "name": agent["name"],
            "focus": agent["focus"],
            "opinion": opinion or "（未产出有效意见）",
            "score": max(0, min(100, int(score_m.group(1)))) if score_m else 60,
            "points": points,
        }

    def _judge(self, contract: str, kb: str, round2: list, has_kb: bool) -> dict:
        debate = "\n\n".join(
            f"【{a['name']}】最终意见：{a['opinion']}\n评分：{a['score']}\n要点：{'；'.join(a['points'])}"
            for a in round2
        )
        user_prompt = (
            f"待审合同《{contract[:1200]}》\n\n三位专家的辩论结论：\n{debate[:2200]}\n\n"
            "你是首席仲裁官，请综合三位专家的辩论结果，给出最终裁决。只输出如下JSON（不要输出其他内容）：\n"
            "{"
            '"verdict": "compliant或needs_revision或non_compliant", '
            '"score": 0到100的整数综合评分, '
            '"dimensions": {"合规性": 分数, "风险控制": 分数, "条款严谨性": 分数, "权益平衡": 分数, "法律完备性": 分数}, '
            '"summary": "150字以内的综合裁决理由", '
            '"optimization": "markdown格式的优化方案，用###开头分点，每点包含具体修改建议"}'
        )
        system = (
            "你是alawyer平台的首席合同仲裁官，具有30年合同纠纷审判经验。你只输出JSON。评分必须从严：凡存在违反法律强制性规定、显失公平或重大风险条款的合同，总分不得高于60分；仅存在表述瑕疵的，总分不得高于80分。"
            "verdict取值：compliant=基本符合法律要求，needs_revision=存在需修正的问题，non_compliant=存在重大违法违规。"
            + ("知识库参考：\n" + kb[:800] if has_kb else "")
        )
        try:
            data = ollama.chat_json(
                [{"role": "system", "content": system}, {"role": "user", "content": user_prompt}],
                temperature=0.3,
            )
        except Exception:
            data = None
        if not isinstance(data, dict) or "verdict" not in data:
            scores = [a["score"] for a in round2] or [60]
            data = {
                "verdict": "needs_revision",
                "score": int(sum(scores) / len(scores)),
                "dimensions": {
                    "合规性": round2[0]["score"] if round2 else 60,
                    "风险控制": round2[1]["score"] if len(round2) > 1 else 60,
                    "条款严谨性": round2[2]["score"] if len(round2) > 2 else 60,
                },
                "summary": "（仲裁官暂不可用，已采用专家平均分作为参考结论）",
                "optimization": "### 优化方案暂时不可用\n请稍后重新发起审查，或联系律师人工复核。",
            }
        if data.get("verdict") not in VERDICT_MAP:
            data["verdict"] = "needs_revision"
        try:
            data["score"] = max(0, min(100, int(float(data.get("score", 60)))))
        except (TypeError, ValueError):
            data["score"] = 60
        dims = data.get("dimensions") if isinstance(data.get("dimensions"), dict) else {}
        clean_dims = {}
        for k, v in dims.items():
            try:
                clean_dims[str(k)[:10]] = max(0, min(100, int(float(v))))
            except (TypeError, ValueError):
                continue
        if not clean_dims:
            clean_dims = {"合规性": data["score"], "风险控制": data["score"], "条款严谨性": data["score"]}
        data["dimensions"] = clean_dims
        if not str(data.get("optimization") or "").strip():
            data["optimization"] = "### 优化方案生成失败\n请重新发起审查获取优化建议。"
        return data


contract_agents = ContractReviewOrchestrator()