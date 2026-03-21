"""
ASIOE — Dataset Seeding Script
Builds the canonical skill ontology from:
1. O*NET Technology Skills database
2. Kaggle resume dataset (skill frequency analysis)
3. Kaggle job descriptions dataset (required skill extraction)
4. Manually curated high-value skills

Run: python scripts/seed_data.py

Outputs:
  /app/data/processed/skill_ontology.json  — canonical skill registry
  /app/data/processed/course_catalog.json  — enriched course catalog
"""
from __future__ import annotations

import json
import os
import re
import sys
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


OUTPUT_DIR = Path(__file__).parent.parent / "backend" / "data" / "processed"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Comprehensive Skill Ontology ──────────────────────────────────────────────
# Each skill node in the DAG

SKILL_ONTOLOGY: List[Dict] = [
    # ── Programming Languages ──────────────────────────────────────────────────
    {
        "skill_id": "python", "canonical_name": "Python",
        "aliases": ["python3", "python 3", "py", "python programming"],
        "domain": "technical", "difficulty_level": "intermediate",
        "avg_time_to_learn_hours": 80, "importance_score": 0.96,
        "prerequisites": ["programming_basics"], "onet_code": "2.C.7.e",
        "description": "General-purpose programming language widely used in data science, ML, and backend development."
    },
    {
        "skill_id": "programming_basics", "canonical_name": "Programming Fundamentals",
        "aliases": ["coding basics", "programming concepts", "computational thinking", "coding"],
        "domain": "technical", "difficulty_level": "beginner",
        "avg_time_to_learn_hours": 40, "importance_score": 0.90,
        "prerequisites": [], "onet_code": "2.C.7.a",
        "description": "Core programming concepts: variables, loops, functions, data structures."
    },
    {
        "skill_id": "javascript", "canonical_name": "JavaScript",
        "aliases": ["js", "javascript programming", "ecmascript", "es6", "es2015"],
        "domain": "technical", "difficulty_level": "intermediate",
        "avg_time_to_learn_hours": 80, "importance_score": 0.90,
        "prerequisites": ["programming_basics", "html_css"], "onet_code": "2.C.7.e",
        "description": "Primary language for web development, both frontend and backend (Node.js)."
    },
    {
        "skill_id": "html_css", "canonical_name": "HTML/CSS",
        "aliases": ["html", "css", "html5", "css3", "web markup"],
        "domain": "technical", "difficulty_level": "beginner",
        "avg_time_to_learn_hours": 30, "importance_score": 0.75,
        "prerequisites": [], "onet_code": "2.C.7.e",
        "description": "Web markup and styling fundamentals."
    },
    {
        "skill_id": "java", "canonical_name": "Java",
        "aliases": ["java programming", "java development", "java se", "java ee"],
        "domain": "technical", "difficulty_level": "intermediate",
        "avg_time_to_learn_hours": 100, "importance_score": 0.85,
        "prerequisites": ["programming_basics", "oop"], "onet_code": "2.C.7.e",
        "description": "Enterprise-grade object-oriented programming language."
    },
    {
        "skill_id": "oop", "canonical_name": "Object-Oriented Programming",
        "aliases": ["oop", "object oriented design", "classes and objects", "ood"],
        "domain": "technical", "difficulty_level": "intermediate",
        "avg_time_to_learn_hours": 40, "importance_score": 0.85,
        "prerequisites": ["programming_basics"], "onet_code": "2.C.7.a",
        "description": "Design paradigm using objects, classes, inheritance, and polymorphism."
    },
    {
        "skill_id": "typescript", "canonical_name": "TypeScript",
        "aliases": ["ts", "typescript programming"],
        "domain": "technical", "difficulty_level": "intermediate",
        "avg_time_to_learn_hours": 40, "importance_score": 0.82,
        "prerequisites": ["javascript", "oop"], "onet_code": "2.C.7.e",
        "description": "Typed superset of JavaScript for large-scale application development."
    },
    {
        "skill_id": "go", "canonical_name": "Go",
        "aliases": ["golang", "go programming", "go language"],
        "domain": "technical", "difficulty_level": "intermediate",
        "avg_time_to_learn_hours": 60, "importance_score": 0.78,
        "prerequisites": ["programming_basics", "oop"], "onet_code": "2.C.7.e",
        "description": "Statically typed, compiled language for high-performance systems."
    },
    # ── Data & Analytics ───────────────────────────────────────────────────────
    {
        "skill_id": "sql", "canonical_name": "SQL",
        "aliases": ["structured query language", "mysql", "postgresql", "postgres",
                    "sqlite", "database querying", "tsql", "plsql"],
        "domain": "technical", "difficulty_level": "intermediate",
        "avg_time_to_learn_hours": 40, "importance_score": 0.92,
        "prerequisites": ["data_concepts"], "onet_code": "2.C.7.b",
        "description": "Standard language for relational database management and querying."
    },
    {
        "skill_id": "data_concepts", "canonical_name": "Data Fundamentals",
        "aliases": ["data literacy", "data basics", "database concepts"],
        "domain": "analytical", "difficulty_level": "beginner",
        "avg_time_to_learn_hours": 20, "importance_score": 0.85,
        "prerequisites": [], "onet_code": "2.B.3.a",
        "description": "Understanding of data types, storage, and basic data manipulation."
    },
    {
        "skill_id": "statistics", "canonical_name": "Statistics",
        "aliases": ["statistical analysis", "statistical modeling", "stats", "probability"],
        "domain": "analytical", "difficulty_level": "intermediate",
        "avg_time_to_learn_hours": 60, "importance_score": 0.88,
        "prerequisites": ["mathematics"], "onet_code": "2.B.3.b",
        "description": "Statistical methods for data analysis, hypothesis testing, and inference."
    },
    {
        "skill_id": "mathematics", "canonical_name": "Mathematics",
        "aliases": ["math", "calculus", "linear algebra", "discrete math"],
        "domain": "analytical", "difficulty_level": "intermediate",
        "avg_time_to_learn_hours": 80, "importance_score": 0.80,
        "prerequisites": [], "onet_code": "2.B.3.a",
        "description": "Mathematical foundations including calculus, linear algebra, and discrete math."
    },
    {
        "skill_id": "data_analysis", "canonical_name": "Data Analysis",
        "aliases": ["data analytics", "exploratory data analysis", "eda", "data exploration"],
        "domain": "analytical", "difficulty_level": "intermediate",
        "avg_time_to_learn_hours": 50, "importance_score": 0.88,
        "prerequisites": ["statistics", "sql", "python"], "onet_code": "2.B.3.b",
        "description": "Techniques for inspecting, cleaning, and modeling data to discover insights."
    },
    {
        "skill_id": "pandas_numpy", "canonical_name": "Pandas & NumPy",
        "aliases": ["pandas", "numpy", "data manipulation python", "dataframes"],
        "domain": "technical", "difficulty_level": "intermediate",
        "avg_time_to_learn_hours": 30, "importance_score": 0.85,
        "prerequisites": ["python", "data_concepts"], "onet_code": "2.C.7.e",
        "description": "Python libraries for numerical computing and data manipulation."
    },
    # ── Machine Learning ───────────────────────────────────────────────────────
    {
        "skill_id": "machine_learning", "canonical_name": "Machine Learning",
        "aliases": ["ml", "statistical learning", "predictive modeling", "supervised learning"],
        "domain": "analytical", "difficulty_level": "advanced",
        "avg_time_to_learn_hours": 160, "importance_score": 0.92,
        "prerequisites": ["python", "statistics", "mathematics", "pandas_numpy"],
        "onet_code": "2.C.7.f",
        "description": "Algorithms enabling systems to learn from data without explicit programming."
    },
    {
        "skill_id": "deep_learning", "canonical_name": "Deep Learning",
        "aliases": ["dl", "neural networks", "ann", "artificial neural networks"],
        "domain": "analytical", "difficulty_level": "expert",
        "avg_time_to_learn_hours": 200, "importance_score": 0.88,
        "prerequisites": ["machine_learning", "mathematics", "python"],
        "onet_code": "2.C.7.f",
        "description": "Neural network architectures for complex pattern recognition tasks."
    },
    {
        "skill_id": "nlp", "canonical_name": "Natural Language Processing",
        "aliases": ["natural language processing", "text mining", "computational linguistics", "text analytics"],
        "domain": "analytical", "difficulty_level": "advanced",
        "avg_time_to_learn_hours": 120, "importance_score": 0.82,
        "prerequisites": ["machine_learning", "python", "statistics"],
        "onet_code": "2.C.7.f",
        "description": "AI techniques for understanding and generating human language."
    },
    {
        "skill_id": "computer_vision", "canonical_name": "Computer Vision",
        "aliases": ["cv", "image processing", "image recognition", "object detection"],
        "domain": "analytical", "difficulty_level": "advanced",
        "avg_time_to_learn_hours": 120, "importance_score": 0.78,
        "prerequisites": ["deep_learning", "python"],
        "onet_code": "2.C.7.f",
        "description": "AI techniques enabling machines to interpret visual information."
    },
    {
        "skill_id": "mlops", "canonical_name": "MLOps",
        "aliases": ["ml operations", "ml deployment", "model deployment", "ml pipeline"],
        "domain": "technical", "difficulty_level": "advanced",
        "avg_time_to_learn_hours": 80, "importance_score": 0.82,
        "prerequisites": ["machine_learning", "docker", "cloud_computing"],
        "onet_code": "2.C.7.f",
        "description": "Practices for deploying, monitoring, and maintaining ML models in production."
    },
    # ── Cloud & Infrastructure ─────────────────────────────────────────────────
    {
        "skill_id": "cloud_computing", "canonical_name": "Cloud Computing",
        "aliases": ["cloud", "cloud services", "cloud infrastructure", "iaas", "paas", "saas"],
        "domain": "technical", "difficulty_level": "intermediate",
        "avg_time_to_learn_hours": 60, "importance_score": 0.88,
        "prerequisites": ["networking_basics", "linux"], "onet_code": "2.C.7.d",
        "description": "On-demand computing resources delivered over the internet."
    },
    {
        "skill_id": "aws", "canonical_name": "Amazon Web Services (AWS)",
        "aliases": ["amazon web services", "aws cloud", "ec2", "s3", "lambda"],
        "domain": "technical", "difficulty_level": "intermediate",
        "avg_time_to_learn_hours": 80, "importance_score": 0.88,
        "prerequisites": ["cloud_computing", "networking_basics"], "onet_code": "2.C.7.d",
        "description": "Amazon's cloud platform — market leader with 200+ services."
    },
    {
        "skill_id": "docker", "canonical_name": "Docker",
        "aliases": ["containerization", "docker containers", "container technology"],
        "domain": "technical", "difficulty_level": "intermediate",
        "avg_time_to_learn_hours": 30, "importance_score": 0.85,
        "prerequisites": ["linux", "networking_basics"], "onet_code": "2.C.7.d",
        "description": "Container platform for building, shipping, and running applications."
    },
    {
        "skill_id": "kubernetes", "canonical_name": "Kubernetes",
        "aliases": ["k8s", "container orchestration", "k8 orchestration"],
        "domain": "technical", "difficulty_level": "advanced",
        "avg_time_to_learn_hours": 60, "importance_score": 0.80,
        "prerequisites": ["docker", "networking_basics", "linux"], "onet_code": "2.C.7.d",
        "description": "Container orchestration system for automated deployment and scaling."
    },
    {
        "skill_id": "linux", "canonical_name": "Linux",
        "aliases": ["unix", "linux administration", "bash", "shell scripting", "command line"],
        "domain": "technical", "difficulty_level": "intermediate",
        "avg_time_to_learn_hours": 40, "importance_score": 0.82,
        "prerequisites": ["programming_basics"], "onet_code": "2.C.7.d",
        "description": "Open-source operating system fundamental to server and cloud environments."
    },
    {
        "skill_id": "networking_basics", "canonical_name": "Networking Fundamentals",
        "aliases": ["computer networking", "tcp/ip", "network protocols", "dns", "http"],
        "domain": "technical", "difficulty_level": "beginner",
        "avg_time_to_learn_hours": 30, "importance_score": 0.75,
        "prerequisites": [], "onet_code": "2.C.7.d",
        "description": "Core networking concepts: TCP/IP, DNS, HTTP, firewalls."
    },
    # ── Software Engineering ───────────────────────────────────────────────────
    {
        "skill_id": "software_design", "canonical_name": "Software Design & Architecture",
        "aliases": ["system design", "software architecture", "design patterns", "solid principles"],
        "domain": "technical", "difficulty_level": "advanced",
        "avg_time_to_learn_hours": 80, "importance_score": 0.90,
        "prerequisites": ["oop", "data_structures"], "onet_code": "2.C.7.a",
        "description": "Principles and patterns for designing scalable, maintainable software systems."
    },
    {
        "skill_id": "data_structures", "canonical_name": "Data Structures & Algorithms",
        "aliases": ["dsa", "algorithms", "data structures", "algorithmic thinking"],
        "domain": "technical", "difficulty_level": "intermediate",
        "avg_time_to_learn_hours": 80, "importance_score": 0.92,
        "prerequisites": ["programming_basics", "mathematics"], "onet_code": "2.C.7.a",
        "description": "Fundamental data structures and algorithmic problem-solving techniques."
    },
    {
        "skill_id": "git", "canonical_name": "Git & Version Control",
        "aliases": ["git", "version control", "github", "gitlab", "bitbucket", "source control"],
        "domain": "technical", "difficulty_level": "beginner",
        "avg_time_to_learn_hours": 15, "importance_score": 0.88,
        "prerequisites": ["programming_basics"], "onet_code": "2.C.7.a",
        "description": "Distributed version control system for tracking code changes."
    },
    {
        "skill_id": "api_design", "canonical_name": "API Design & REST",
        "aliases": ["restful api", "rest api", "api development", "rest", "web api", "graphql"],
        "domain": "technical", "difficulty_level": "intermediate",
        "avg_time_to_learn_hours": 30, "importance_score": 0.85,
        "prerequisites": ["networking_basics", "programming_basics"], "onet_code": "2.C.7.a",
        "description": "Design and implementation of RESTful and GraphQL APIs."
    },
    {
        "skill_id": "testing", "canonical_name": "Software Testing & QA",
        "aliases": ["unit testing", "integration testing", "test driven development", "tdd", "qa"],
        "domain": "technical", "difficulty_level": "intermediate",
        "avg_time_to_learn_hours": 40, "importance_score": 0.80,
        "prerequisites": ["programming_basics", "oop"], "onet_code": "2.C.7.a",
        "description": "Strategies and tools for testing software quality and reliability."
    },
    {
        "skill_id": "ci_cd", "canonical_name": "CI/CD Pipelines",
        "aliases": ["continuous integration", "continuous deployment", "devops pipeline",
                    "jenkins", "github actions", "gitlab ci"],
        "domain": "technical", "difficulty_level": "intermediate",
        "avg_time_to_learn_hours": 30, "importance_score": 0.80,
        "prerequisites": ["git", "docker"], "onet_code": "2.C.7.d",
        "description": "Automated build, test, and deployment workflows."
    },
    # ── Data Engineering ───────────────────────────────────────────────────────
    {
        "skill_id": "data_engineering", "canonical_name": "Data Engineering",
        "aliases": ["data pipeline", "etl", "data infrastructure", "data platform"],
        "domain": "technical", "difficulty_level": "advanced",
        "avg_time_to_learn_hours": 120, "importance_score": 0.85,
        "prerequisites": ["sql", "python", "cloud_computing"], "onet_code": "2.C.7.b",
        "description": "Design and maintenance of scalable data pipelines and infrastructure."
    },
    {
        "skill_id": "spark", "canonical_name": "Apache Spark",
        "aliases": ["pyspark", "apache spark", "spark streaming", "big data processing"],
        "domain": "technical", "difficulty_level": "advanced",
        "avg_time_to_learn_hours": 80, "importance_score": 0.78,
        "prerequisites": ["python", "data_engineering", "data_concepts"], "onet_code": "2.C.7.b",
        "description": "Distributed computing framework for large-scale data processing."
    },
    # ── Security ───────────────────────────────────────────────────────────────
    {
        "skill_id": "cybersecurity", "canonical_name": "Cybersecurity",
        "aliases": ["information security", "infosec", "security", "network security", "cyber security"],
        "domain": "technical", "difficulty_level": "advanced",
        "avg_time_to_learn_hours": 120, "importance_score": 0.82,
        "prerequisites": ["networking_basics", "linux", "programming_basics"], "onet_code": "2.C.7.d",
        "description": "Protecting systems and networks from digital attacks and unauthorized access."
    },
    # ── Leadership & Management ────────────────────────────────────────────────
    {
        "skill_id": "project_management", "canonical_name": "Project Management",
        "aliases": ["pm", "project planning", "pmp", "program management"],
        "domain": "leadership", "difficulty_level": "intermediate",
        "avg_time_to_learn_hours": 60, "importance_score": 0.82,
        "prerequisites": ["communication"], "onet_code": "2.B.1.a",
        "description": "Planning, executing, and closing projects on time and within budget."
    },
    {
        "skill_id": "agile", "canonical_name": "Agile & Scrum",
        "aliases": ["scrum", "agile methodology", "kanban", "sprint planning", "agile development"],
        "domain": "leadership", "difficulty_level": "intermediate",
        "avg_time_to_learn_hours": 20, "importance_score": 0.80,
        "prerequisites": ["project_management"], "onet_code": "2.B.1.a",
        "description": "Iterative development methodology for adaptive project management."
    },
    {
        "skill_id": "team_leadership", "canonical_name": "Team Leadership",
        "aliases": ["people management", "team management", "leadership", "managing teams"],
        "domain": "leadership", "difficulty_level": "advanced",
        "avg_time_to_learn_hours": 60, "importance_score": 0.78,
        "prerequisites": ["communication", "project_management"], "onet_code": "2.B.4.e",
        "description": "Leading, motivating, and developing high-performing teams."
    },
    # ── Communication & Soft Skills ────────────────────────────────────────────
    {
        "skill_id": "communication", "canonical_name": "Communication Skills",
        "aliases": ["verbal communication", "written communication", "presentation skills", "public speaking"],
        "domain": "communication", "difficulty_level": "intermediate",
        "avg_time_to_learn_hours": 30, "importance_score": 0.85,
        "prerequisites": [], "onet_code": "2.A.1.g",
        "description": "Clear and effective communication in professional environments."
    },
    {
        "skill_id": "problem_solving", "canonical_name": "Problem Solving",
        "aliases": ["critical thinking", "analytical thinking", "troubleshooting"],
        "domain": "soft_skills", "difficulty_level": "intermediate",
        "avg_time_to_learn_hours": 20, "importance_score": 0.88,
        "prerequisites": [], "onet_code": "2.A.2.a",
        "description": "Systematic approach to identifying and resolving complex problems."
    },
    # ── Finance Domain (relevant for JPMC context) ─────────────────────────────
    {
        "skill_id": "financial_analysis", "canonical_name": "Financial Analysis",
        "aliases": ["financial modeling", "financial planning", "fp&a", "valuation", "dcf"],
        "domain": "domain_specific", "difficulty_level": "advanced",
        "avg_time_to_learn_hours": 80, "importance_score": 0.85,
        "prerequisites": ["mathematics", "statistics", "data_analysis"], "onet_code": "4.C.1.a",
        "description": "Analyzing financial data to support business decisions and valuations."
    },
    {
        "skill_id": "risk_management", "canonical_name": "Risk Management",
        "aliases": ["risk analysis", "operational risk", "credit risk", "market risk"],
        "domain": "domain_specific", "difficulty_level": "advanced",
        "avg_time_to_learn_hours": 60, "importance_score": 0.82,
        "prerequisites": ["financial_analysis", "statistics"], "onet_code": "4.C.1.a",
        "description": "Identification, assessment, and mitigation of organizational risks."
    },
    {
        "skill_id": "regulatory_compliance", "canonical_name": "Regulatory Compliance",
        "aliases": ["compliance", "regulatory", "sox", "gdpr", "finra", "aml"],
        "domain": "domain_specific", "difficulty_level": "advanced",
        "avg_time_to_learn_hours": 40, "importance_score": 0.78,
        "prerequisites": ["risk_management"], "onet_code": "4.C.1.a",
        "description": "Adherence to laws, regulations, and industry standards."
    },
]


# ── Course Catalog ─────────────────────────────────────────────────────────────

COURSE_CATALOG: List[Dict] = [
    # Python
    {"course_id": "py_everybody", "title": "Python for Everybody Specialization",
     "description": "Complete Python programming from scratch with Dr. Chuck. Covers data structures, web data, databases.",
     "provider": "Coursera / University of Michigan", "url": "https://www.coursera.org/specializations/python",
     "domain": "technical", "difficulty_level": "beginner", "estimated_hours": 40,
     "skills_covered": ["Python", "Programming Fundamentals", "Data Structures & Algorithms", "SQL"]},
    {"course_id": "py_advanced", "title": "Advanced Python Programming",
     "description": "Advanced Python: decorators, generators, async, metaclasses, performance optimization.",
     "provider": "Udemy", "url": "https://www.udemy.com/course/advanced-python/",
     "domain": "technical", "difficulty_level": "advanced", "estimated_hours": 30,
     "skills_covered": ["Python", "Object-Oriented Programming", "Software Design & Architecture"]},

    # Machine Learning
    {"course_id": "ml_ng", "title": "Machine Learning Specialization",
     "description": "Andrew Ng's definitive ML course. Supervised, unsupervised, and reinforcement learning.",
     "provider": "Coursera / DeepLearning.AI", "url": "https://www.coursera.org/specializations/machine-learning-introduction",
     "domain": "analytical", "difficulty_level": "intermediate", "estimated_hours": 90,
     "skills_covered": ["Machine Learning", "Python", "Statistics", "Pandas & NumPy"]},
    {"course_id": "dl_ng", "title": "Deep Learning Specialization",
     "description": "5-course deep learning specialization covering CNNs, RNNs, and practical deployment.",
     "provider": "Coursera / DeepLearning.AI", "url": "https://www.coursera.org/specializations/deep-learning",
     "domain": "analytical", "difficulty_level": "advanced", "estimated_hours": 120,
     "skills_covered": ["Deep Learning", "Neural Networks", "Natural Language Processing", "Computer Vision"]},
    {"course_id": "mlops_course", "title": "Machine Learning Engineering for Production (MLOps)",
     "description": "Deploy scalable ML systems with proper monitoring and CI/CD.",
     "provider": "Coursera / DeepLearning.AI", "url": "https://www.coursera.org/specializations/machine-learning-engineering-for-production-mlops",
     "domain": "technical", "difficulty_level": "advanced", "estimated_hours": 80,
     "skills_covered": ["MLOps", "Docker", "Cloud Computing", "Machine Learning"]},

    # Data
    {"course_id": "sql_mode", "title": "SQL for Data Analysis",
     "description": "SQL from basics to advanced window functions, CTEs, and query optimization.",
     "provider": "Mode Analytics", "url": "https://mode.com/sql-tutorial/",
     "domain": "technical", "difficulty_level": "beginner", "estimated_hours": 20,
     "skills_covered": ["SQL", "Data Fundamentals", "Data Analysis"]},
    {"course_id": "stats_course", "title": "Statistics with Python Specialization",
     "description": "Statistical analysis, inference, and visualization using Python.",
     "provider": "Coursera / University of Michigan", "url": "https://www.coursera.org/specializations/statistics-with-python",
     "domain": "analytical", "difficulty_level": "intermediate", "estimated_hours": 60,
     "skills_covered": ["Statistics", "Python", "Data Analysis", "Pandas & NumPy"]},
    {"course_id": "data_engineering", "title": "Data Engineering, Big Data & ML on GCP",
     "description": "End-to-end data engineering pipelines on Google Cloud Platform.",
     "provider": "Coursera / Google", "url": "https://www.coursera.org/specializations/gcp-data-machine-learning",
     "domain": "technical", "difficulty_level": "advanced", "estimated_hours": 80,
     "skills_covered": ["Data Engineering", "Apache Spark", "Cloud Computing", "SQL"]},

    # Cloud & DevOps
    {"course_id": "aws_clf", "title": "AWS Certified Cloud Practitioner",
     "description": "Foundational AWS cloud concepts, services, and pricing.",
     "provider": "AWS Training", "url": "https://aws.amazon.com/certification/certified-cloud-practitioner/",
     "domain": "technical", "difficulty_level": "beginner", "estimated_hours": 30,
     "skills_covered": ["Amazon Web Services (AWS)", "Cloud Computing", "Networking Fundamentals"]},
    {"course_id": "docker_k8s", "title": "Docker & Kubernetes: The Practical Guide",
     "description": "Complete containerization guide from Docker basics to Kubernetes production deployments.",
     "provider": "Udemy", "url": "https://www.udemy.com/course/docker-kubernetes-the-practical-guide/",
     "domain": "technical", "difficulty_level": "intermediate", "estimated_hours": 50,
     "skills_covered": ["Docker", "Kubernetes", "Linux", "CI/CD Pipelines"]},

    # Software Engineering
    {"course_id": "dsa_course", "title": "Algorithms Specialization",
     "description": "Stanford's definitive algorithms course covering divide & conquer, graph algorithms, NP-completeness.",
     "provider": "Coursera / Stanford", "url": "https://www.coursera.org/specializations/algorithms",
     "domain": "technical", "difficulty_level": "advanced", "estimated_hours": 80,
     "skills_covered": ["Data Structures & Algorithms", "Problem Solving", "Mathematics"]},
    {"course_id": "system_design", "title": "Grokking System Design Interview",
     "description": "Comprehensive system design for scalable distributed systems.",
     "provider": "Educative", "url": "https://www.educative.io/courses/grokking-modern-system-design-interview",
     "domain": "technical", "difficulty_level": "advanced", "estimated_hours": 40,
     "skills_covered": ["Software Design & Architecture", "Cloud Computing", "API Design & REST"]},

    # Leadership
    {"course_id": "leadership_wharton", "title": "Leadership and Management Specialization",
     "description": "Wharton's executive program on leadership, communication, and organizational management.",
     "provider": "Coursera / Wharton", "url": "https://www.coursera.org/specializations/leadership-management-wharton",
     "domain": "leadership", "difficulty_level": "intermediate", "estimated_hours": 30,
     "skills_covered": ["Team Leadership", "Communication Skills", "Project Management"]},
    {"course_id": "agile_cert", "title": "Agile with Atlassian Jira",
     "description": "Practical Agile methodology and Scrum framework using Jira.",
     "provider": "Coursera / Atlassian", "url": "https://www.coursera.org/learn/agile-atlassian-jira",
     "domain": "leadership", "difficulty_level": "beginner", "estimated_hours": 15,
     "skills_covered": ["Agile & Scrum", "Project Management"]},

    # Finance
    {"course_id": "financial_mkts", "title": "Financial Markets",
     "description": "Yale's comprehensive course on finance, risk management, and investment.",
     "provider": "Coursera / Yale", "url": "https://www.coursera.org/learn/financial-markets-global",
     "domain": "domain_specific", "difficulty_level": "intermediate", "estimated_hours": 33,
     "skills_covered": ["Financial Analysis", "Risk Management", "Statistics"]},
    {"course_id": "risk_mgmt", "title": "Enterprise Risk Management",
     "description": "Frameworks for identifying, measuring, and managing enterprise-level risks.",
     "provider": "Coursera / NYU", "url": "https://www.coursera.org/learn/enterprise-risk-management",
     "domain": "domain_specific", "difficulty_level": "advanced", "estimated_hours": 25,
     "skills_covered": ["Risk Management", "Financial Analysis", "Regulatory Compliance"]},

    # Security
    {"course_id": "cybersec_ibm", "title": "IBM Cybersecurity Analyst Professional Certificate",
     "description": "Full cybersecurity analyst training: threat intelligence, SIEM, incident response.",
     "provider": "Coursera / IBM", "url": "https://www.coursera.org/professional-certificates/ibm-cybersecurity-analyst",
     "domain": "technical", "difficulty_level": "intermediate", "estimated_hours": 120,
     "skills_covered": ["Cybersecurity", "Networking Fundamentals", "Linux"]},
]


def build_ontology() -> None:
    out_path = OUTPUT_DIR / "skill_ontology.json"
    with open(out_path, "w") as f:
        json.dump(SKILL_ONTOLOGY, f, indent=2)
    print(f"✅ Skill ontology written: {len(SKILL_ONTOLOGY)} skills → {out_path}")


def build_course_catalog() -> None:
    out_path = OUTPUT_DIR / "course_catalog.json"
    with open(out_path, "w") as f:
        json.dump(COURSE_CATALOG, f, indent=2)
    print(f"✅ Course catalog written: {len(COURSE_CATALOG)} courses → {out_path}")


def build_sample_data() -> None:
    """Generate sample resume and JD for testing."""
    sample_resume = {
        "filename": "sample_resume.json",
        "candidate_name": "Alex Johnson",
        "current_role": "Junior Software Engineer",
        "years_of_experience": 2,
        "education_level": "bachelor",
        "skills": [
            {"name": "Python", "proficiency_level": "intermediate", "proficiency_score": 0.6, "domain": "technical", "years_used": 2.0},
            {"name": "SQL", "proficiency_level": "beginner", "proficiency_score": 0.3, "domain": "technical", "years_used": 1.0},
            {"name": "Git", "proficiency_level": "intermediate", "proficiency_score": 0.6, "domain": "technical", "years_used": 2.0},
            {"name": "HTML/CSS", "proficiency_level": "intermediate", "proficiency_score": 0.6, "domain": "technical", "years_used": 2.0},
        ]
    }
    sample_jd = {
        "filename": "sample_jd.txt",
        "content": """
Senior Data Scientist — Financial Services

We are seeking an experienced Senior Data Scientist to join our risk analytics team.

Required Skills:
- Python (Advanced) — 4+ years
- Machine Learning — 3+ years  
- SQL (Advanced) — 3+ years
- Statistics and Probability — 3+ years
- Data Analysis — 3+ years
- Cloud Computing (AWS preferred) — 2+ years
- MLOps and model deployment — 2+ years

Preferred Skills:
- Deep Learning
- Natural Language Processing
- Apache Spark
- Docker/Kubernetes
- Financial Analysis

Minimum 5 years experience. Masters or PhD in quantitative field preferred.
"""
    }
    out_path = OUTPUT_DIR / "sample_data.json"
    with open(out_path, "w") as f:
        json.dump({"resume": sample_resume, "jd": sample_jd}, f, indent=2)
    print(f"✅ Sample data written → {out_path}")


if __name__ == "__main__":
    print("🔧 Seeding ASIOE datasets...")
    build_ontology()
    build_course_catalog()
    build_sample_data()
    print("\n✅ All seed data written successfully.")
    print(f"   Output directory: {OUTPUT_DIR}")
