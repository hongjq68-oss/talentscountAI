"""Built-in recruiting knowledge used for the no-LLM fallback mode and for scoring."""

SKILLS = {
    "Languages": ["Python", "Java", "JavaScript", "TypeScript", "Go", "Golang", "Rust", "C++", "C#", "Scala",
                  "Kotlin", "Swift", "Ruby", "PHP", "SQL", "R", "Solidity", "Elixir", "Dart"],
    "Frontend": ["React", "Next.js", "Vue", "Angular", "Svelte", "Redux", "Tailwind", "HTML", "CSS", "React Native",
                 "Flutter", "iOS", "Android"],
    "Backend": ["Node.js", "Django", "Flask", "FastAPI", "Spring", "Spring Boot", ".NET", "Rails", "GraphQL",
                "REST", "gRPC", "Microservices", "Kafka", "RabbitMQ", "Redis"],
    "Data & AI": ["Machine Learning", "Deep Learning", "NLP", "LLM", "Generative AI", "Computer Vision", "PyTorch",
                  "TensorFlow", "scikit-learn", "Spark", "Airflow", "dbt", "Snowflake", "Databricks", "BigQuery",
                  "Data Engineering", "Data Science", "Analytics", "Tableau", "Power BI", "MLOps", "RAG",
                  "Statistics", "A/B Testing", "Pandas"],
    "Cloud & Infra": ["AWS", "GCP", "Azure", "Kubernetes", "Docker", "Terraform", "CI/CD", "Linux", "DevOps",
                      "SRE", "Observability", "Security", "Networking", "Serverless"],
    "Databases": ["PostgreSQL", "MySQL", "MongoDB", "DynamoDB", "Cassandra", "Elasticsearch", "Oracle"],
    "Product & Design": ["Product Management", "Roadmap", "UX", "UI Design", "Figma", "User Research",
                         "Product Strategy", "Agile", "Scrum", "OKRs"],
    "Business & Leadership": ["Leadership", "People Management", "Stakeholder Management", "P&L", "Strategy",
                              "Go-to-Market", "Sales", "Business Development", "Partnerships", "Fundraising",
                              "M&A", "Budgeting", "Change Management", "Transformation", "Board",
                              "Hiring", "Mentoring", "Cross-functional", "Negotiation", "Account Management",
                              "Enterprise Sales", "SaaS", "B2B", "B2C", "Marketing", "Growth", "SEO",
                              "Brand", "Operations", "Supply Chain", "Procurement"],
    "Finance & Risk": ["Financial Modelling", "FP&A", "Accounting", "IFRS", "GAAP", "Audit", "Compliance",
                       "Risk Management", "AML", "KYC", "Treasury", "Payments", "Trading", "Investment Banking",
                       "Private Equity", "Credit", "Regulatory"],
    "People": ["Talent Acquisition", "HRBP", "Compensation", "Employee Relations", "L&D", "Workday"],
}
ALL_SKILLS = [(s, cat) for cat, items in SKILLS.items() for s in items]

GITHUB_LANG = {
    "Python": "python", "Java": "java", "JavaScript": "javascript", "TypeScript": "typescript", "Go": "go",
    "Golang": "go", "Rust": "rust", "C++": "c++", "C#": "c#", "Scala": "scala", "Kotlin": "kotlin",
    "Swift": "swift", "Ruby": "ruby", "PHP": "php", "Solidity": "solidity", "Elixir": "elixir", "Dart": "dart",
    "React": "javascript", "Node.js": "javascript", "Next.js": "typescript", "Django": "python",
    "FastAPI": "python", "PyTorch": "python", "TensorFlow": "python", "Machine Learning": "python",
    "Spring": "java", "Spring Boot": "java", "Flutter": "dart", "iOS": "swift", "Android": "kotlin",
}

SENIORITY = [
    ("C-Level", ["chief", "ceo", "cto", "cfo", "coo", "cpo", "cmo", "ciso", "cio", "chro"]),
    ("VP / Head", ["vice president", "vp ", "vp,", "svp", "evp", "head of", "general manager", "managing director"]),
    ("Director", ["director"]),
    ("Manager / Lead", ["manager", "lead", "principal", "staff"]),
    ("Senior IC", ["senior", "sr.", "sr "]),
    ("Mid-level IC", ["engineer", "analyst", "specialist", "associate", "consultant", "developer", "scientist"]),
]

INDUSTRY_KEYWORDS = {
    "Fintech & Payments": ["payment", "fintech", "wallet", "lending", "neobank", "card", "remittance"],
    "Banking & Financial Services": ["bank", "wealth", "asset management", "insurance", "capital markets"],
    "E-commerce & Marketplaces": ["e-commerce", "ecommerce", "marketplace", "retail", "merchant", "logistics"],
    "AI & Machine Learning": ["artificial intelligence", "machine learning", "llm", "generative ai", " ai "],
    "Enterprise SaaS": ["saas", "b2b", "enterprise software", "subscription"],
    "Consumer Internet": ["consumer", "social", "gaming", "media", "streaming", "superapp", "super app", "mobility", "ride-hailing", "deliveries"],
    "Healthcare & Life Sciences": ["health", "clinical", "pharma", "biotech", "medical", "patient"],
    "Crypto & Web3": ["crypto", "blockchain", "web3", "defi", "token"],
    "Cybersecurity": ["cybersecurity", "security operations", "threat", "soc ", "zero trust"],
    "Semiconductors & Hardware": ["semiconductor", "chip", "hardware", "silicon", "embedded"],
    "Consulting & Professional Services": ["consulting", "advisory", "client engagement"],
}

INDUSTRY_COMPANIES = {
    "Fintech & Payments": ["Stripe", "Adyen", "PayPal", "Block", "Wise", "Revolut", "Grab Financial", "Airwallex",
                           "Nium", "Checkout.com", "Klarna", "Ant Group", "Visa", "Mastercard", "Rapyd"],
    "Banking & Financial Services": ["JPMorgan Chase", "Goldman Sachs", "Morgan Stanley", "DBS", "HSBC",
                                     "Standard Chartered", "Citi", "UBS", "OCBC", "UOB", "BlackRock", "Barclays"],
    "E-commerce & Marketplaces": ["Amazon", "Shopee", "Lazada", "Alibaba", "Tokopedia", "Shopify", "eBay",
                                  "Coupang", "Mercado Libre", "Zalando", "Flipkart", "Temu"],
    "AI & Machine Learning": ["OpenAI", "Anthropic", "Google DeepMind", "Meta AI", "Microsoft", "NVIDIA",
                              "Cohere", "Mistral AI", "Hugging Face", "Databricks", "Scale AI", "Perplexity"],
    "Enterprise SaaS": ["Salesforce", "ServiceNow", "Atlassian", "Workday", "HubSpot", "Snowflake", "Datadog",
                        "Okta", "Zendesk", "Canva", "Freshworks", "Twilio", "MongoDB"],
    "Consumer Internet": ["Google", "Meta", "ByteDance", "TikTok", "Netflix", "Spotify", "Sea Group", "Grab",
                          "Uber", "Airbnb", "Gojek", "Snap"],
    "Healthcare & Life Sciences": ["Johnson & Johnson", "Pfizer", "Roche", "Novartis", "Philips Healthcare",
                                   "GE HealthCare", "Siemens Healthineers", "AstraZeneca", "Medtronic"],
    "Crypto & Web3": ["Coinbase", "Binance", "Kraken", "OKX", "Crypto.com", "Circle", "Chainalysis",
                      "Consensys", "Ripple"],
    "Cybersecurity": ["CrowdStrike", "Palo Alto Networks", "Fortinet", "Zscaler", "SentinelOne", "Okta",
                      "Cloudflare", "Check Point"],
    "Semiconductors & Hardware": ["NVIDIA", "AMD", "Intel", "Qualcomm", "TSMC", "Broadcom", "Micron",
                                  "ASML", "Apple", "Samsung"],
    "Consulting & Professional Services": ["McKinsey", "BCG", "Bain", "Deloitte", "PwC", "EY", "KPMG",
                                           "Accenture", "Oliver Wyman"],
}

LOCATIONS = ["Singapore", "Hong Kong", "London", "New York", "San Francisco", "Bay Area", "Seattle", "Austin",
             "Boston", "Toronto", "Sydney", "Melbourne", "Tokyo", "Seoul", "Shanghai", "Beijing", "Shenzhen",
             "Bangalore", "Bengaluru", "Mumbai", "Delhi", "Hyderabad", "Jakarta", "Kuala Lumpur", "Bangkok",
             "Manila", "Ho Chi Minh", "Dubai", "Berlin", "Paris", "Amsterdam", "Dublin", "Zurich", "Remote"]
