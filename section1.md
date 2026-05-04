- ### 数据处理与图谱构建流程

    1. **写入 Source / Chunk**：采集原始网页或文本，清洗并切分为证据片段（Chunk），补充来源元数据。
    2. **从 Chunk 抽取 Claim**：利用大模型从证据片段中提取结构化的原子断言（Claim）。
    3. **写入 Claims**：将提取出的断言数据落库保存。
    4. **根据 Claim 生成 KG_Node / KG_Edge**：将断言的主体、客体和关系映射为知识图谱（KG）的实体节点与结构边，构建稳定的“设定骨架”。
    5. **对 Claim 两两检测支持、冲突、限制关系**：通过 NLI/LLM 对断言进行比对，识别它们之间的逻辑关联与矛盾。
    6. **写入 Claim Edges**：将断言间的关系落库保存，保留设定分歧与场景差异。

    ------

    ### 职责边界说明

    在深入具体实现细节前，需明确双图架构的职责划分原则，核心思想是“知识图谱节点和边必须由断言支撑，不从 AI 总结中直接凭空生成”：

    - **知识图谱 (Knowledge Graph)**：负责保存“世界中有什么？它们如何相连？”。存储相对稳定的设定骨架（实体、事件、基础关系），去除矛盾，作为基础设定查询的依托。
    - **断言图 (Claim Graph)**：负责保存“谁说了什么？证据是什么？说法间是否冲突？”。显式保留矛盾与来源差异，用于 OOC 检测、正史/粉丝区分及创作分支推荐。

    ------

    ### 各步骤实现细节与落库参考

    #### 第一步：写入 Source / Chunk

    - **实现细节**：通过合法脚本采集网页，清洗 HTML 与无关噪音。将文本切分为 `evidence_chunk`，并基于规则（如域名或目录）预先打上 `source_type` 标签（如 `primary_canon`, `fan_consensus`）。
    - **前置输出**：生成基础的 Chunk 数据集，为后续抽取提供引用来源（对应后续的 `source_id` 和 `chunk_id`）。

    #### 第二步：从 Chunk 抽取 Claim

    - **实现细节**：将切分好的 Chunk 输入大语言模型，要求模型抽取结构化三元组（主体、谓词、客体）。系统需对抽取的断言赋予分类标签，包括 `claim_type`（如特质、价值观、世界规则）以及分类状态（`canon_status`, `fan_status` 等）。同时保留置信度与证据片段摘要。

    #### 第三步：写入 Claims

    - **实现细节**：将第二步清洗并格式化后的数据作为断言节点（Claim Node）写入断言图系统。

    - **参考模板 (`claims.jsonl`)**：

        JSON

        ```
        {
          "claim_id": "clm_000001",
          "claim_text": "钟离高度重视契约与承诺。",
          "work": "原神",
          "subject": {
            "entity_id": "char_zhongli",
            "name": "钟离",
            "type": "character"
          },
          "predicate": "values",
          "object": {
            "value": "契约与承诺",
            "type": "value"
          },
          "claim_type": "value_or_worldview",
          "source_support": [
            {
              "source_id": "src_000001",
              "chunk_id": "chk_000001",
              "source_type": "primary_canon",
              "evidence_quote": "可引用的短证据片段。",
              "support_strength": 0.92
            }
          ],
          "classification": {
            "canon_status": "canon_anchored",
            "fan_status": "not_fan_based",
            "branch_status": "mainline",
            "ooc_relevance": "high"
          },
          "confidence": {
            "extraction_confidence": 0.88,
            "source_reliability": 1.0,
            "overall_confidence": 0.91
          },
          "review_status": "pending_human_review"
        }
        ```

    #### 第四步：根据 Claim 生成 KG_Node / KG_Edge

    - **实现细节**：遍历 `claims.jsonl` 中的数据。将断言中的 `subject` 和 `object` 抽取为知识图谱的节点（如果尚未存在），将 `predicate` 映射为知识图谱的边。每个节点和边都必须关联其对应的 `claim_ids` 和 `source_ids`，以确保“设定骨架”具有可追溯的溯源证明。

    - **参考模板 (`kg_nodes.jsonl`)**：

        JSON

        ```
        {
          "node_id": "char_zhongli",
          "node_type": "character",
          "name": "钟离",
          "aliases": ["摩拉克斯", "岩王帝君"],
          "work": "原神",
          "attributes": {
            "identity": "往生堂客卿"
          },
          "source_ids": ["src_000001"],
          "claim_ids": ["clm_000001"],
          "confidence": 0.95,
          "review_status": "pending_human_review"
        }
        ```

    - **参考模板 (`kg_edges.jsonl`)**：

        JSON

        ```
        {
          "edge_id": "edge_000001",
          "from_node": "char_zhongli",
          "to_node": "value_contract",
          "edge_type": "values",
          "work": "原神",
          "claim_ids": ["clm_000001"],
          "source_ids": ["src_000001"],
          "confidence": 0.91,
          "review_status": "pending_human_review"
        }
        ```

    #### 第五步：对 Claim 两两检测支持、冲突、限制关系

    - **实现细节**：在保留出处的情况下，对提取出的断言运行成对的自然语言推理（NLI）或通过 LLM 进行检测。重点识别断言间的关系（如 `supports`, `conflicts_with`），如果存在冲突，需明确聚类其冲突类型（如 `value_conflict`, `timeline_conflict`）并判定严重程度（`severity`）。

    #### 第六步：写入 Claim Edges

    - **实现细节**：将第五步生成的冲突或支持关系写入断言图边表。这是整个系统防止“单源重复”、提供多样化场景适配和 OOC 检测的基础数据层。

    - **参考模板 (`claim_edges.jsonl`)**：

        JSON

        ```
        {
          "claim_edge_id": "cedge_000001",
          "from_claim_id": "clm_000001",
          "to_claim_id": "clm_000002",
          "relation_type": "conflicts_with",
          "conflict_type": "value_conflict",
          "explanation": "两个断言在角色核心价值观层面存在冲突。",
          "severity": "high",
          "confidence": 0.86,
          "source_ids": ["src_000001", "src_000002"],
          "evidence_chunk_ids": ["chk_000001", "chk_000002"],
          "detected_by": "nli_conflict_detector_v1",
          "review_status": "pending_human_review"
        }
        ```

    Ad astra abyssosque