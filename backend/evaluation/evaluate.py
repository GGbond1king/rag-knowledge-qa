"""
RAG检索评估脚本 - 自包含测试集 + 三模式对比

用法:
    cd backend && venv/Scripts/python.exe evaluation/evaluate.py

输出: 纯向量 / 纯BM25 / 双路RRF 三种模式 Recall@K 对比表
"""
import sys, os, textwrap, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.retriever import InMemoryVectorStore, BM25Index
from core.llm_manager import LLMManager


# ====== 内置测试文档 ======
TEST_DOCUMENTS = [
    {   # 0
        "filename": "transformer_intro.txt",
        "content": textwrap.dedent("""\
            Transformer是一种基于自注意力机制的神经网络架构，由Vaswani等人在2017年提出。
            其核心创新是自注意力(Self-Attention)机制，允许模型在处理每个位置的输入时，
            直接关注所有其他位置的信息，而不是像RNN那样按顺序逐步处理长距离依赖。
            Transformer由编码器(Encoder)和解码器(Decoder)组成。编码器将输入序列映射为连续表示，
            解码器则基于这些表示生成输出序列。每个编码器层都由多头注意力(Multi-Head Attention)
            和前馈神经网络(Feed-Forward Network)组成。BERT、GPT等预训练模型都基于Transformer架构。
            自注意力机制使模型能够捕捉长距离依赖关系，这是RNN难以做到的。Transformer还使用了
            位置编码(Positional Encoding)来保留序列中单词的顺序信息。多头注意力允许模型同时关注
            不同位置的表示子空间的信息。Transformer架构已经被广泛应用于自然语言处理、计算机视觉
            和语音识别等领域。其并行计算能力使得训练速度远超传统的RNN模型。""")
    },
    {   # 1
        "filename": "rag_overview.txt",
        "content": textwrap.dedent("""\
            检索增强生成(Retrieval-Augmented Generation, RAG)是一种结合信息检索和文本生成的技术。
            传统的大语言模型只能依赖训练时学到的参数化知识，无法访问外部信息或被遗忘的数据。
            RAG通过在生成回答前先从外部知识库中检索相关文档，然后将检索结果作为上下文输入给语言模型，
            从而显著提高了回答的准确性和时效性。RAG系统通常包含三个核心步骤：首先将用户问题通过
            Embedding模型转化为向量，然后在向量数据库中进行相似度检索找到最相关的文档片段，
            最后将检索结果和原始问题一起构建prompt输入给大语言模型生成答案。向量数据库通常使用
            余弦相似度或点积来衡量文本向量之间的语义相似度。RAG的优势在于可以实时更新知识库而无需
            重新训练模型，有效解决了LLM知识过时和幻觉问题。优秀的检索质量直接影响RAG系统的最终效果，
            因此检索策略的设计是RAG系统最关键的部分之一。""")
    },
    {   # 2
        "filename": "crispr_intro.txt",
        "content": textwrap.dedent("""\
            CRISPR-Cas9是一种革命性的基因编辑技术，它源自细菌的免疫防御系统。
            CRISPR代表成簇规律间隔短回文重复序列，是细菌用来记住入侵病毒DNA序列的记忆系统。
            Cas9是一种核酸内切酶，可以在特定位置切割DNA双链。研究人员通过设计人工的guide RNA，
            来引导Cas9蛋白精确到达目标基因序列的特定位置，然后在DNA双链断裂处进行基因编辑操作，
            包括基因敲除、基因插入和基因修正。CRISPR技术的应用范围非常广泛，包括人类基因治疗、
            农业作物改良、疾病动物模型构建以及传染病诊断等领域。CRISPR-Cas9因其设计简单、
            编辑高效、靶点精准和成本低廉的特点，已成为目前最广泛使用的基因编辑工具。
            然而CRISPR技术也面临脱靶效应和伦理争议等挑战，科学家们正在不断改进其精准性和安全性。
            除了CRISPR-Cas9，还有Cas12和Cas13等其他CRISPR系统，它们具有不同的特性和应用场景。""")
    },
    {   # 3
        "filename": "python_basics.txt",
        "content": textwrap.dedent("""\
            Python是一种高级编程语言，由Guido van Rossum于1991年创建，以其简洁易读的语法和强大的功能著称。
            列表推导式(List Comprehension)是Python最独特的语法特性之一，可以用一行简洁的代码生成列表，
            例如：squares = [x**2 for x in range(10)]会生成0到9的平方数列表。Python支持多种编程范式，
            包括面向对象编程、函数式编程和过程式编程。Python拥有丰富的标准库，涵盖了文件I/O操作、
            网络通信协议、数据序列化、正则表达式、单元测试和日期时间处理等常见任务。在数据科学领域，
            常用的第三方库包括NumPy（数值计算）、Pandas（数据分析）、Matplotlib（数据可视化）、
            Scikit-learn（机器学习）和TensorFlow/PyTorch（深度学习）。Python的包管理工具pip使得安装
            第三方库非常方便。Python的虚拟环境(virtualenv/venv)可以帮助隔离不同项目的依赖关系，
            避免版本冲突问题。Python在Web开发、自动化脚本、数据分析和人工智能领域都有广泛应用。""")
    },
    {   # 4
        "filename": "climate_change.txt",
        "content": textwrap.dedent("""\
            气候变化是当今全球面临的最严峻的环境挑战之一。科学研究表明，温室气体的大量排放是导致
            全球变暖的主要原因。主要的温室气体包括二氧化碳(CO2)、甲烷(CH4)和氧化亚氮(N2O)。
            自工业革命以来，人类活动导致大气中的二氧化碳浓度从约280ppm急剧上升到了超过420ppm，
            这是至少过去80万年来的最高水平。全球平均气温已比工业化前水平升高了约1.2摄氏度，
            如果各国不采取积极行动，本世纪末升温可能达到3摄氏度以上。应对气候变化的主要措施包括
            减少化石燃料使用、大力发展太阳能和风能等可再生能源、提高各行业的能源利用效率、
            推广电动汽车替代燃油车、实施碳捕集与封存技术以及保护和恢复森林生态系统。
            国际社会通过《巴黎协定》等框架合作应对气候变化，各国承诺了各自的减排目标。
            中国提出了2030年前碳达峰和2060年前碳中和的目标，这是应对气候变化的重要贡献。""")
    },
    {   # 5 (distractor - 也提到了深度学习但面向不同主题)
        "filename": "deep_learning_overview.txt",
        "content": textwrap.dedent("""\
            深度学习是机器学习的一个子领域，它使用多层神经网络来学习数据的层次化特征表示。
            深度神经网络包含输入层、多个隐藏层和输出层，每一层都由大量相互连接的神经元组成。
            卷积神经网络(CNN)擅长处理图像数据，通过卷积操作提取局部特征；循环神经网络(RNN)
            适合处理序列数据如文本和语音，但存在梯度消失问题。Transformer架构使用自注意力机制
            替代了RNN中的循环结构，大大提高了并行计算效率和长距离依赖建模能力。训练深度神经网络
            通常需要大量标注数据和强大的计算资源（GPU或TPU）。反向传播算法和梯度下降优化器
            （如Adam、SGD）是训练深度网络的核心算法。常见的深度学习框架包括TensorFlow、PyTorch
            和Keras，其中PyTorch因其动态图和易用性在学术界和研究领域最受欢迎。深度学习的应用
            覆盖计算机视觉、自然语言处理、语音识别、推荐系统和自动驾驶等多个领域。""")
    },
    {   # 6 (distractor - 提到了搜索但面向另一主题)
        "filename": "information_retrieval.txt",
        "content": textwrap.dedent("""\
            信息检索(Information Retrieval, IR)是从大规模文档集合中寻找满足用户信息需求的内容的过程。
            传统的信息检索系统主要基于关键词匹配，使用TF-IDF或BM25等算法来评估文档与查询的相关性。
            BM25算法是TF-IDF的改进版本，它考虑了文档长度归一化和词频饱和效应，在实际搜索系统中
            表现优异。随着深度学习的发展，基于向量的语义检索逐渐成为主流。语义检索通过Embedding模型
            将查询和文档映射到同一个向量空间，然后计算余弦相似度来度量语义相关性。向量检索的优点
            是可以理解同义词和近义词，克服了传统关键词检索的词汇不匹配问题。混合检索系统结合了
            关键词检索和语义检索的优点，通过倒数排名融合(RRF)等算法将两种检索结果合并。
            Elasticsearch和Milvus是业界常用的检索系统，分别擅长关键词搜索和向量搜索。""")
    },
    {   # 7 (distractor - 提到了biology但面向另一主题)
        "filename": "dna_sequencing.txt",
        "content": textwrap.dedent("""\
            DNA测序技术是分子生物学研究的基础工具，用于确定DNA分子中核苷酸(A、T、C、G)的精确排列顺序。
            第一代测序技术基于Sanger测序法，虽然准确率高但通量低、成本高。第二代测序技术（如Illumina平台）
            通过大规模并行测序大大提高了通量，将人类基因组测序成本从数十亿美元降低到了数千美元。
            第三代测序技术包括Pacific Biosciences和Oxford Nanopore Technology，能够直接测序单个
            DNA分子，产生更长的读长但准确率略低。DNA测序在医学诊断、法医鉴定、物种鉴定和进化研究
            中有广泛应用。全基因组测序可以检测与疾病相关的基因突变，指导个性化医疗。然而DNA测序
            产生的海量数据对生物信息学分析提出了巨大挑战，需要高性能计算和专业的分析流程来从原始
            数据中提取有意义的生物学信息。基因编辑技术如CRISPR可以与测序技术结合，实现对基因组的
            精确修饰和检测。""")
    },
]

# 生成更多干扰文档，使检索任务具有区分度
TOPICS = [
    ("computer_vision.txt", "计算机视觉是人工智能领域的重要分支，主要研究如何让计算机从图像和视频中理解视觉信息。"),
    ("nlp_intro.txt", "自然语言处理(NLP)是AI的重要方向，致力于让计算机理解和生成人类语言。"),
    ("reinforcement_learning.txt", "强化学习是机器学习的一种范式，智能体通过与环境交互学习最优策略。"),
    ("data_mining.txt", "数据挖掘是从大量数据中发现隐藏模式、关联和知识的过程。"),
    ("cloud_computing.txt", "云计算通过网络提供按需的计算资源、存储和应用服务。"),
    ("sql_database.txt", "SQL是结构化查询语言的缩写，用于管理关系数据库中的数据。"),
    ("git_version_control.txt", "Git是目前最流行的分布式版本控制系统，用于跟踪代码变更。"),
    ("linux_commands.txt", "Linux是一种开源操作系统，广泛用于服务器和嵌入式系统。"),
    ("docker_container.txt", "Docker是一种容器化平台，将应用及其依赖打包在标准化的容器中。"),
    ("kubernetes_cluster.txt", "Kubernetes是一个容器编排平台，自动化容器的部署、扩展和管理。"),
    ("rest_api.txt", "REST API是基于HTTP协议的应用程序接口设计风格，使用GET、POST等标准方法。"),
    ("microservice_arch.txt", "微服务架构将应用拆分为一组小型独立服务，每个服务专注单一业务功能。"),
    ("blockchain_tech.txt", "区块链是一种去中心化的分布式账本技术，以比特币为代表的加密货币首次应用。"),
    ("edge_computing.txt", "边缘计算将计算和数据存储靠近数据源，降低延迟和带宽使用。"),
    ("quantum_computing.txt", "量子计算利用量子力学原理，通过量子比特实现超越经典计算机的计算能力。"),
    ("web_scraping.txt", "网络爬虫是自动化从网站提取数据的程序，常用于数据采集和信息监测。"),
    ("api_gateway.txt", "API网关是微服务架构中的入口网关，负责请求路由、认证限流等功能。"),
    ("ci_cd.txt", "CI/CD是持续集成和持续交付的缩写，自动化构建测试部署流程提高软件交付效率。"),
    ("oauth2_auth.txt", "OAuth2是一种开放授权协议，允许第三方应用获取有限的资源访问权限。"),
    ("graphql_api.txt", "GraphQL是一种API查询语言，允许客户端精确指定所需的数据结构。"),
]

curr_idx = 8
for topic_name, topic_desc in TOPICS:
    TEST_DOCUMENTS.append({
        "filename": topic_name,
        "content": textwrap.dedent(f"""\
            {topic_desc}
            这是一个关于{topic_name.replace('.txt','').replace('_','')}技术的详细介绍。
            在实际应用中，这项技术已经广泛被采用，并且有很多成熟的工具和框架支持。
            开发人员需要理解其核心概念和最佳实践，以便在工程项目中正确使用。
            随着技术的不断演进，新的方法和工具也在持续涌现，推动着整个行业的进步。
            学习和掌握这些知识对于技术人员的职业发展至关重要。""")
    })

# ====== 测试查询 ======
TEST_QUERIES = [
    {"id": "q1",  "query": "什么是Transformer自注意力机制", "expect": ["transformer_intro.txt"]},
    {"id": "q2",  "query": "RAG检索增强生成是什么", "expect": ["rag_overview.txt"]},
    {"id": "q3",  "query": "CRISPR-Cas9基因编辑原理", "expect": ["crispr_intro.txt"]},
    {"id": "q4",  "query": "Python列表推导式怎么用", "expect": ["python_basics.txt"]},
    {"id": "q5",  "query": "编码器解码器结构", "expect": ["transformer_intro.txt"]},
    {"id": "q6",  "query": "向量数据库在RAG中的作用", "expect": ["rag_overview.txt"]},
    {"id": "q7",  "query": "如何减少温室气体排放", "expect": ["climate_change.txt"]},
    {"id": "q8",  "query": "Cas9蛋白切割DNA双链", "expect": ["crispr_intro.txt"]},
    {"id": "q9",  "query": "Python的数据处理库有哪些", "expect": ["python_basics.txt"]},
    {"id": "q10", "query": "温室气体导致全球变暖", "expect": ["climate_change.txt"]},
    {"id": "q11", "query": "GPT基于什么架构", "expect": ["transformer_intro.txt"]},
    {"id": "q12", "query": "BM25和TF-IDF区别", "expect": ["information_retrieval.txt"]},
    {"id": "q13", "query": "深度学习卷积神经网络CNN", "expect": ["deep_learning_overview.txt"]},
    {"id": "q14", "query": "DNA测序技术的原理", "expect": ["dna_sequencing.txt"]},
    {"id": "q15", "query": "NNLM与RNN梯度消失", "expect": ["deep_learning_overview.txt"]},
    {"id": "q16", "query": "倒数排名融合RRF算法", "expect": ["information_retrieval.txt"]},
    {"id": "q17", "query": "CRISPR脱靶效应伦理", "expect": ["crispr_intro.txt"]},
    {"id": "q18", "query": "《巴黎协定》碳达峰碳中和", "expect": ["climate_change.txt"]},
    {"id": "q19", "query": "Sanger测序法基本原理", "expect": ["dna_sequencing.txt"]},
    {"id": "q20", "query": "PyTorch比TensorFlow优势", "expect": ["deep_learning_overview.txt"]},
]


def build_chunks(text: str, chunk_size: int = 400):
    """将文本切分为chunk"""
    sentences = text.replace("\n", "").split("。")
    chunks = []
    current = ""
    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        if len(current) + len(sent) < chunk_size:
            current += sent + "。"
        else:
            if current:
                chunks.append(current.strip())
            current = sent + "。"
    if current:
        chunks.append(current.strip())
    return chunks if chunks else [text]


async def build_test_index():
    """构建测试用的向量库和BM25索引"""
    print("=" * 60)
    print("构建测试索引 (8 documents)...")
    print("=" * 60)

    store = InMemoryVectorStore(persist_path="./data/eval_test.pkl")
    bm25 = BM25Index()
    llm = LLMManager()

    total_chunks = 0
    for doc in TEST_DOCUMENTS:
        chunks = build_chunks(doc["content"])
        source_id = doc["filename"].replace(".", "_")

        all_embeddings = []
        chunk_objects = []
        for i, chunk_text in enumerate(chunks):
            metadata = {
                "source_id": source_id,
                "filename": doc["filename"],
                "chunk_index": i,
            }
            emb = await llm.get_embedding(chunk_text)
            all_embeddings.append(emb)
            chunk_objects.append((chunk_text, metadata))

        ids = [f"{source_id}_{i}" for i in range(len(chunks))]
        store.upsert(ids=ids, embeddings=all_embeddings,
                     documents=[c[0] for c in chunk_objects],
                     metadatas=[c[1] for c in chunk_objects])
        total_chunks += len(chunks)
        print(f"  [+] {doc['filename']} -> {len(chunks)} chunks")

    store._ensure_loaded()
    bm25.rebuild(store.vectors)
    print(f"\n  共 {total_chunks} 个chunk, 索引构建完成")
    return store, bm25, llm


async def evaluate_query(store, bm25, llm, query_text, expected_set, top_k=2):
    """单query三模式评估"""
    emb = await llm.get_embedding(query_text)

    # 纯向量
    vec = store.query(emb, top_k=top_k)
    r_vec = _recall(vec["metadatas"][0], expected_set)

    # 纯BM25
    bm = bm25.search(query_text, top_k=top_k)
    r_bm25 = _recall([r["metadata"] for r in bm], expected_set)

    # 双路RRF
    r_rrf = _rrf_search(store, bm25, emb, query_text, top_k, expected_set)

    return r_vec, r_bm25, r_rrf


def _recall(metadatas, expected_set):
    retrieved = set(m.get("filename", "") for m in metadatas)
    if not expected_set:
        return 0.0
    return len(retrieved & expected_set) / len(expected_set)


def _rrf_search(store, bm25, emb, query_text, top_k, expected_set):
    K = 60
    fetch_k = max(top_k * 3, 12)
    vec_r = store.query(emb, top_k=fetch_k)
    bm25_r = bm25.search(query_text, top_k=fetch_k)

    score_map = {}
    for rank, (content, meta) in enumerate(zip(vec_r["documents"][0], vec_r["metadatas"][0])):
        sim = 1 - vec_r["distances"][0][rank]
        if sim < 0.05:
            continue
        score_map[content[:100]] = {"rrf": 1.0/(K+rank), "filename": meta.get("filename", "")}

    for rank, item in enumerate(bm25_r):
        key = item["content"][:100]
        if key not in score_map:
            score_map[key] = {"rrf": 0.0, "filename": item["metadata"].get("filename", "")}
        score_map[key]["rrf"] += 1.0 / (K + rank)

    sorted_res = sorted(score_map.values(), key=lambda x: x["rrf"], reverse=True)
    retrieved = set(it["filename"] for it in sorted_res[:top_k])
    if not expected_set:
        return 0.0
    return len(retrieved & expected_set) / len(expected_set)


async def main():
    store, bm25, llm = await build_test_index()

    print("\n" + "=" * 60)
    print("开始评估 (top_k=2, 共8目标文档+20干扰文档)")
    print("=" * 60)

    all_results = []
    for q in TEST_QUERIES:
        rv, rb, rh = await evaluate_query(store, bm25, llm, q["query"], set(q["expect"]))
        all_results.append({**q, "vec": rv, "bm25": rb, "rrf": rh})

    # 对比表
    print(f"\n  {'Query':<28} {'向量':>7} {'BM25':>7} {'RRF':>7} 最佳")
    print(f"  {'-'*28} {'-'*7} {'-'*7} {'-'*7} {'-'*6}")
    for r in all_results:
        best = max(r["vec"], r["bm25"], r["rrf"])
        m = "RRF" if r["rrf"] >= best and r["rrf"] > 0 else \
            "BM25" if r["bm25"] >= best and r["bm25"] > 0 else \
            "向量" if r["vec"] >= best and r["vec"] > 0 else "-"
        print(f"  {r['query']:<28} {r['vec']:>6.0%} {r['bm25']:>6.0%} {r['rrf']:>6.0%}  [{m}]")

    # 平均
    avg_v = sum(r["vec"] for r in all_results) / len(all_results)
    avg_b = sum(r["bm25"] for r in all_results) / len(all_results)
    avg_h = sum(r["rrf"] for r in all_results) / len(all_results)
    print(f"  {'-'*28} {'-'*7} {'-'*7} {'-'*7}")
    print(f"  {'平均 Recall@2':<28} {avg_v:>6.0%} {avg_b:>6.0%} {avg_h:>6.0%}")

    if avg_v > 0:
        print(f"\n  RRF vs 向量: +{((avg_h-avg_v)/avg_v*100):+.0f}%")
    if avg_b > 0:
        print(f"  RRF vs BM25: +{((avg_h-avg_b)/avg_b*100):+.0f}%")

    # 胜出统计
    v_w = sum(1 for r in all_results if r["vec"] > r["bm25"] and r["vec"] > r["rrf"])
    b_w = sum(1 for r in all_results if r["bm25"] > r["vec"] and r["bm25"] > r["rrf"])
    h_w = sum(1 for r in all_results if r["rrf"] >= r["vec"] and r["rrf"] >= r["bm25"] and r["rrf"] > 0)
    tie_all = sum(1 for r in all_results if r["vec"] == r["bm25"] == r["rrf"] and r["rrf"] > 0)
    print(f"\n  [最优] 向量胜:{v_w}  BM25胜:{b_w}  RRF胜:{h_w}  平局:{tie_all}")
    print(f"\n  测试集: {len(TEST_QUERIES)} queries x {len(TEST_DOCUMENTS)} docs")
    print(f"  评估完成!")


if __name__ == "__main__":
    asyncio.run(main())
