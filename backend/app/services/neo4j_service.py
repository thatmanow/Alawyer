from app.config import settings


class Neo4jService:
    def __init__(self):
        self.driver = None

    def _ensure_driver(self):
        if self.driver is not None:
            return True
        try:
            from neo4j import GraphDatabase

            driver = GraphDatabase.driver(
                settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
            )
            driver.verify_connectivity()
            self.driver = driver
        except Exception:
            self.driver = None
        return self.driver is not None

    def available(self) -> bool:
        return self._ensure_driver()

    def _run(self, cypher, **params):
        if not self.available():
            return []
        try:
            with self.driver.session() as session:
                return list(session.run(cypher, **params))
        except Exception:
            self.driver = None
            return []

    def clear_graph(self):
        if not self.available():
            return
        self._run("MATCH (n) DETACH DELETE n")

    def build_from_documents(self, docs: list):
        """docs: [{id, name, domain, keywords: [str]}]"""
        if not self.available():
            return
        self._run("MATCH (n) DETACH DELETE n")
        for d in docs:
            self._run(
                "MERGE (doc:Document {id: $id}) SET doc.name = $name",
                id=int(d["id"]), name=d["name"],
            )
            self._run(
                "MERGE (dom:Domain {name: $domain}) "
                "MERGE (doc:Document {id: $id}) "
                "MERGE (doc)-[:BELONGS_TO]->(dom)",
                domain=d["domain"], id=int(d["id"]),
            )
            for kw in d.get("keywords", []):
                self._run(
                    "MERGE (k:Keyword {name: $kw}) "
                    "MERGE (doc:Document {id: $id}) "
                    "MERGE (doc)-[:MENTIONS]->(k)",
                    kw=kw, id=int(d["id"]),
                )
        self._run(
            "MATCH (d1:Document)-[:MENTIONS]->(k:Keyword)<-[:MENTIONS]-(d2:Document) "
            "WHERE id(d1) < id(d2) "
            "MERGE (d1)-[:SHARES_KEYWORD {name: k.name}]->(d2)"
        )

    def remove_document(self, doc_id: int):
        if not self.available():
            return
        self._run(
            "MATCH (d:Document {id: $id})-[r]-() DELETE r WITH d DETACH DELETE d", id=int(doc_id)
        )
        self._run(
            "MATCH (k:Keyword) WHERE NOT ()-[:MENTIONS]->(k) DELETE k"
        )

    def add_document(self, doc: dict):
        """增量添加单个文档节点及其关系"""
        if not self.available():
            return
        self._run(
            "MERGE (doc:Document {id: $id}) SET doc.name = $name",
            id=int(doc["id"]), name=doc["name"],
        )
        self._run(
            "MERGE (dom:Domain {name: $domain}) "
            "MERGE (doc:Document {id: $id}) "
            "MERGE (doc)-[:BELONGS_TO]->(dom)",
            domain=doc["domain"], id=int(doc["id"]),
        )
        for kw in doc.get("keywords", []):
            self._run(
                "MERGE (k:Keyword {name: $kw}) "
                "MERGE (doc:Document {id: $id}) "
                "MERGE (doc)-[:MENTIONS]->(k)",
                kw=kw, id=int(doc["id"]),
            )

    def get_graph(self, max_docs: int = 60) -> dict:
        if not self.available():
            return {"nodes": [], "links": []}
        nodes, links, seen_nodes, seen_links = [], [], set(), set()
        for record in self._run(
            "MATCH (a)-[r]->(b) RETURN a, type(r) AS rel, b LIMIT 500"
        ):
            for node in (record["a"], record["b"]):
                elem_id = node.element_id
                if elem_id in seen_nodes:
                    continue
                seen_nodes.add(elem_id)
                labels = list(node.labels)
                label = labels[0] if labels else "Node"
                name = node.get("name") or f"{label}-{node.get('id', '')}"
                nodes.append({"id": elem_id, "name": name, "label": label, "size": 20})
            key = (record["a"].element_id, record["b"].element_id, record["rel"])
            if key not in seen_links:
                seen_links.add(key)
                links.append(
                    {"source": record["a"].element_id, "target": record["b"].element_id, "type": record["rel"]}
                )
        return {"nodes": nodes, "links": links}

    def domain_stats(self) -> list:
        if not self.available():
            return []
        records = self._run(
            "MATCH (d:Document)-[:BELONGS_TO]->(dom:Domain) "
            "RETURN dom.name AS name, count(d) AS value ORDER BY value DESC"
        )
        return [{"name": r["name"], "value": r["value"]} for r in records]


neo4j_service = Neo4jService()