"""
Interview preparation engine.

Provides interview session management, question generation from a built-in
question bank, and deterministic response evaluation with optional LLM
enhancement.
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class Question(BaseModel):
    """A single interview question."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    question: str
    category: str = Field(
        ...,
        description="technical, behavioral, system_design, or coding",
    )
    difficulty: str = Field(
        ...,
        description="easy, medium, or hard",
    )
    role: str
    skills_tested: list[str] = Field(default_factory=list)
    sample_answer: str = ""
    follow_ups: list[str] = Field(default_factory=list)


class Evaluation(BaseModel):
    """Evaluation result for a single response."""

    question_id: str
    score: float = Field(..., ge=0, le=100)
    feedback: str
    strengths: list[str] = Field(default_factory=list)
    areas_for_improvement: list[str] = Field(default_factory=list)
    model_answer: str = ""


class InterviewSession(BaseModel):
    """An active interview practice session."""

    session_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    candidate_id: int
    job_id: Optional[int] = None
    session_type: str
    questions: list[Question] = Field(default_factory=list)
    current_question_index: int = 0
    evaluations: list[Evaluation] = Field(default_factory=list)
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc)
    )
    status: str = "active"


# ---------------------------------------------------------------------------
# Question bank
# ---------------------------------------------------------------------------

QUESTION_BANK: dict[str, dict[str, list[dict[str, Any]]]] = {
    # ======================================================================
    # SOFTWARE ENGINEER
    # ======================================================================
    "software_engineer": {
        "technical": [
            {
                "question": "Explain the difference between a stack and a queue. When would you use each?",
                "difficulty": "easy",
                "skills_tested": ["Data Structures"],
                "sample_answer": "A stack is LIFO (Last In, First Out) – the last element added is the first removed. A queue is FIFO (First In, First Out). Use stacks for undo operations, expression parsing, DFS. Use queues for BFS, task scheduling, buffering.",
                "follow_ups": [
                    "How would you implement a queue using two stacks?",
                    "What is a priority queue and how does it differ?",
                ],
            },
            {
                "question": "What is the time complexity of looking up a key in a hash map? What about worst case?",
                "difficulty": "easy",
                "skills_tested": ["Data Structures", "Algorithms"],
                "sample_answer": "Average case is O(1). Worst case is O(n) when all keys hash to the same bucket (hash collision). Good hash functions and resizing strategies mitigate this.",
                "follow_ups": [
                    "How do hash maps handle collisions?",
                    "What is the difference between open addressing and chaining?",
                ],
            },
            {
                "question": "Explain the SOLID principles and give an example of applying the Single Responsibility Principle.",
                "difficulty": "medium",
                "skills_tested": ["Software Design", "OOP"],
                "sample_answer": "SOLID: Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion. SRP means a class should have one reason to change. Example: separate a UserService (business logic) from a UserRepository (data access).",
                "follow_ups": [
                    "How does the Open/Closed principle relate to inheritance vs composition?",
                    "Give an example of Liskov Substitution violation.",
                ],
            },
            {
                "question": "What is the difference between concurrency and parallelism?",
                "difficulty": "medium",
                "skills_tested": ["Systems Programming", "Python"],
                "sample_answer": "Concurrency is about dealing with multiple tasks at once (interleaving). Parallelism is about executing multiple tasks simultaneously on multiple cores. Python's GIL allows concurrency via async/threading but limits CPU parallelism to multiprocessing.",
                "follow_ups": [
                    "How does Python's asyncio achieve concurrency?",
                    "When would you choose multiprocessing over threading?",
                ],
            },
            {
                "question": "Describe how garbage collection works in Python. What is reference counting?",
                "difficulty": "hard",
                "skills_tested": ["Python", "Memory Management"],
                "sample_answer": "Python uses reference counting as primary GC: each object tracks how many references point to it. When count reaches 0, memory is freed. A cyclic garbage collector handles reference cycles. The gc module allows manual control.",
                "follow_ups": [
                    "What are circular references and how does Python detect them?",
                    "How can memory leaks still occur in Python?",
                ],
            },
        ],
        "behavioral": [
            {
                "question": "Tell me about a time you had to debug a difficult production issue under time pressure.",
                "difficulty": "medium",
                "skills_tested": ["Problem Solving", "Communication"],
                "sample_answer": "Use the STAR method: Situation (production outage), Task (find root cause), Action (systematic investigation: logs, metrics, reproduction), Result (resolved within SLA, implemented monitoring to prevent recurrence).",
                "follow_ups": [
                    "What would you do differently next time?",
                    "How did you communicate the issue to stakeholders?",
                ],
            },
            {
                "question": "Describe a situation where you disagreed with a technical decision. How did you handle it?",
                "difficulty": "medium",
                "skills_tested": ["Communication", "Teamwork"],
                "sample_answer": "STAR: Describe the disagreement objectively, how you presented your concerns with data/evidence, how you listened to the other perspective, and the outcome (compromise, learning, or accepting the decision gracefully).",
                "follow_ups": [
                    "How do you approach code reviews when you disagree?",
                    "What if your suggestion was overruled?",
                ],
            },
            {
                "question": "How do you prioritize tasks when you have multiple deadlines?",
                "difficulty": "easy",
                "skills_tested": ["Time Management", "Communication"],
                "sample_answer": "I use urgency-importance matrix. Communicate with stakeholders about trade-offs. Break large tasks into smaller deliverables. Use tools like Jira/Trello for visibility. Raise blockers early.",
                "follow_ups": [
                    "How do you handle scope creep?",
                    "What's your approach to estimating task duration?",
                ],
            },
            {
                "question": "Tell me about a project you're most proud of and why.",
                "difficulty": "easy",
                "skills_tested": ["Communication", "Self-awareness"],
                "sample_answer": "Describe the project, your specific contribution, challenges overcome, impact delivered, and what you learned. Focus on measurable outcomes.",
                "follow_ups": [
                    "What would you improve about that project?",
                    "How did you collaborate with the team?",
                ],
            },
            {
                "question": "Describe a time when you had to learn a new technology quickly to deliver a project.",
                "difficulty": "medium",
                "skills_tested": ["Learning Agility", "Adaptability"],
                "sample_answer": "STAR: Context of the project, the technology you needed to learn, your approach (documentation, tutorials, prototyping), time invested, and the successful outcome.",
                "follow_ups": [
                    "What resources do you find most effective for learning?",
                    "How do you decide when to learn something new vs using what you know?",
                ],
            },
        ],
        "system_design": [
            {
                "question": "Design a URL shortening service like bit.ly.",
                "difficulty": "medium",
                "skills_tested": ["System Design", "Databases", "Scalability"],
                "sample_answer": "Components: API gateway, hash generation service (base62 encoding of auto-increment ID or MD5 truncation), relational DB for mappings, cache layer (Redis) for hot URLs, analytics pipeline. Handle collisions, expiry, rate limiting. Scale with read replicas and sharding.",
                "follow_ups": [
                    "How would you handle custom short URLs?",
                    "How would you scale to billions of URLs?",
                    "What caching strategy would you use?",
                ],
            },
            {
                "question": "Design a real-time chat application.",
                "difficulty": "hard",
                "skills_tested": ["System Design", "WebSockets", "Scalability"],
                "sample_answer": "WebSocket connections for real-time messaging. Message broker (Kafka/Redis Pub-Sub) for routing. Store messages in a database (Cassandra for scale). User presence service. Push notifications. End-to-end encryption. Scale with connection servers behind a load balancer.",
                "follow_ups": [
                    "How would you handle offline users?",
                    "How would you implement message delivery guarantees?",
                ],
            },
            {
                "question": "Design a rate limiter for an API.",
                "difficulty": "medium",
                "skills_tested": ["System Design", "Algorithms"],
                "sample_answer": "Algorithms: Token Bucket, Leaky Bucket, Fixed/Sliding Window. Implement with Redis (INCR + EXPIRE). Consider per-user, per-IP, and global limits. Return 429 with Retry-After header. Distribute across instances with a shared store.",
                "follow_ups": [
                    "What's the difference between token bucket and sliding window?",
                    "How would you handle distributed rate limiting?",
                ],
            },
            {
                "question": "How would you design a notification system?",
                "difficulty": "medium",
                "skills_tested": ["System Design", "Message Queues"],
                "sample_answer": "Notification service receives events from upstream services. Route through a message queue (SQS/Kafka) to delivery channels: email (SendGrid), push (Firebase), SMS (Twilio), in-app (WebSocket). Deduplication, user preferences, retry with exponential backoff, delivery tracking.",
                "follow_ups": [
                    "How would you handle notification fatigue?",
                    "How would you ensure at-least-once delivery?",
                ],
            },
            {
                "question": "Design a file storage system like Google Drive.",
                "difficulty": "hard",
                "skills_tested": ["System Design", "Distributed Systems", "Storage"],
                "sample_answer": "Blob storage (S3) for file content, metadata DB (Postgres) for file info/permissions/folder hierarchy, chunked upload for large files, deduplication via content hashing, versioning with copy-on-write, sharing via ACLs, sync client with conflict resolution.",
                "follow_ups": [
                    "How would you handle concurrent edits?",
                    "How would you implement file search?",
                ],
            },
        ],
        "coding": [
            {
                "question": "Write a function to find the two numbers in an array that add up to a target sum.",
                "difficulty": "easy",
                "skills_tested": ["Algorithms", "Data Structures"],
                "sample_answer": "Use a hash map: iterate through the array, for each number check if (target - number) exists in the map. If yes, return the pair. Otherwise add the number to the map. Time: O(n), Space: O(n).",
                "follow_ups": [
                    "What if the array is sorted? Can you do it in O(1) space?",
                    "What if you need to find three numbers?",
                ],
            },
            {
                "question": "Implement a function to check if a string is a valid palindrome, ignoring non-alphanumeric characters.",
                "difficulty": "easy",
                "skills_tested": ["Strings", "Algorithms"],
                "sample_answer": "Two-pointer approach: left pointer at start, right at end. Skip non-alphanumeric characters. Compare characters case-insensitively. Time: O(n), Space: O(1).",
                "follow_ups": [
                    "How would you find the longest palindromic substring?",
                    "What if the string contains Unicode?",
                ],
            },
            {
                "question": "Given a binary tree, write a function to find its maximum depth.",
                "difficulty": "easy",
                "skills_tested": ["Trees", "Recursion"],
                "sample_answer": "Recursive: return 0 for null node, otherwise 1 + max(depth(left), depth(right)). Iterative: use BFS with level counting. Time: O(n), Space: O(h) recursive or O(w) BFS.",
                "follow_ups": [
                    "How would you find the minimum depth?",
                    "Can you do it iteratively?",
                ],
            },
            {
                "question": "Implement an LRU (Least Recently Used) cache with O(1) get and put operations.",
                "difficulty": "hard",
                "skills_tested": ["Data Structures", "Design"],
                "sample_answer": "Use a hash map + doubly linked list. Map stores key → node pointer. List maintains access order. On get: move node to front. On put: add to front, evict from tail if capacity exceeded. Both O(1).",
                "follow_ups": [
                    "How would you make it thread-safe?",
                    "How would you implement an LFU cache?",
                ],
            },
            {
                "question": "Write a function to merge two sorted linked lists into one sorted list.",
                "difficulty": "easy",
                "skills_tested": ["Linked Lists", "Algorithms"],
                "sample_answer": "Create a dummy head node. Use two pointers, compare current values, append the smaller node. When one list is exhausted, append the remainder of the other. Time: O(n+m), Space: O(1).",
                "follow_ups": [
                    "How would you merge k sorted lists?",
                    "Can you do it recursively?",
                ],
            },
        ],
    },
    # ======================================================================
    # DATA SCIENTIST
    # ======================================================================
    "data_scientist": {
        "technical": [
            {
                "question": "Explain the bias-variance tradeoff. How does it affect model selection?",
                "difficulty": "medium",
                "skills_tested": ["Machine Learning", "Statistics"],
                "sample_answer": "Bias is error from overly simplistic model assumptions (underfitting). Variance is error from sensitivity to training data fluctuations (overfitting). The tradeoff: reducing bias increases variance and vice versa. Use cross-validation to find the sweet spot. Regularization (L1/L2) helps control variance.",
                "follow_ups": [
                    "How do ensemble methods address this tradeoff?",
                    "Give an example of a high-bias vs high-variance model.",
                ],
            },
            {
                "question": "What is the difference between L1 and L2 regularization?",
                "difficulty": "medium",
                "skills_tested": ["Machine Learning", "Statistics"],
                "sample_answer": "L1 (Lasso) adds absolute value of coefficients as penalty; produces sparse models (feature selection). L2 (Ridge) adds squared coefficients; shrinks coefficients but rarely sets them to zero. L1 is better for feature selection; L2 when all features are potentially relevant.",
                "follow_ups": [
                    "When would you use Elastic Net?",
                    "How do you choose the regularization parameter?",
                ],
            },
            {
                "question": "How do you handle missing data in a dataset?",
                "difficulty": "easy",
                "skills_tested": ["Data Cleaning", "Pandas"],
                "sample_answer": "Strategies: (1) Remove rows/columns if minimal data loss, (2) Impute with mean/median/mode, (3) Use model-based imputation (KNN, MICE), (4) Create a 'missing' indicator feature. Choice depends on MCAR/MAR/MNAR mechanism and data volume.",
                "follow_ups": [
                    "How do you determine if data is missing at random?",
                    "What are the risks of mean imputation?",
                ],
            },
            {
                "question": "Explain the difference between bagging and boosting.",
                "difficulty": "medium",
                "skills_tested": ["Machine Learning", "Ensemble Methods"],
                "sample_answer": "Bagging (Bootstrap Aggregating): train multiple models on random subsets in parallel, average predictions (reduces variance). Random Forest is an example. Boosting: train models sequentially, each correcting predecessor's errors (reduces bias). XGBoost, AdaBoost are examples.",
                "follow_ups": [
                    "When would you prefer Random Forest over XGBoost?",
                    "How does gradient boosting differ from AdaBoost?",
                ],
            },
            {
                "question": "What is a ROC curve and what does AUC represent?",
                "difficulty": "easy",
                "skills_tested": ["Machine Learning", "Evaluation Metrics"],
                "sample_answer": "ROC (Receiver Operating Characteristic) plots True Positive Rate vs False Positive Rate at various classification thresholds. AUC (Area Under Curve) measures overall model discrimination ability. AUC=1 is perfect, AUC=0.5 is random. Useful for comparing classifiers independent of threshold.",
                "follow_ups": [
                    "When is AUC not a good metric?",
                    "How does precision-recall curve differ?",
                ],
            },
        ],
        "behavioral": [
            {
                "question": "Tell me about a time you communicated a complex analysis to non-technical stakeholders.",
                "difficulty": "medium",
                "skills_tested": ["Communication", "Data Visualization"],
                "sample_answer": "STAR: Describe the analysis, the audience, how you simplified the message (visualizations, analogies, key takeaways), and the outcome (decision made based on your presentation).",
                "follow_ups": [
                    "How do you decide what level of detail to include?",
                    "What visualization tools do you prefer and why?",
                ],
            },
            {
                "question": "Describe a data project that didn't go as planned. What did you learn?",
                "difficulty": "medium",
                "skills_tested": ["Problem Solving", "Resilience"],
                "sample_answer": "STAR: Describe the project, what went wrong (data quality, model performance, scope creep), how you adapted, and the lessons learned (validation, expectation management, iterative approach).",
                "follow_ups": [
                    "How do you set expectations with stakeholders early on?",
                    "What processes do you put in place to catch issues early?",
                ],
            },
            {
                "question": "How do you stay current with developments in data science and ML?",
                "difficulty": "easy",
                "skills_tested": ["Learning Agility"],
                "sample_answer": "Read papers (arXiv, Papers With Code), follow conferences (NeurIPS, ICML), take courses, participate in Kaggle competitions, contribute to open-source, read blogs (Towards Data Science), join communities.",
                "follow_ups": [
                    "What's the most impactful paper you've read recently?",
                    "How do you evaluate which new techniques are worth adopting?",
                ],
            },
            {
                "question": "Tell me about a time you identified a data quality issue that others had missed.",
                "difficulty": "medium",
                "skills_tested": ["Attention to Detail", "Data Quality"],
                "sample_answer": "STAR: Describe how you discovered the issue (EDA, validation checks), the impact it would have had, how you communicated it, and the fix implemented.",
                "follow_ups": [
                    "What data validation checks do you routinely perform?",
                    "How do you build trust in your data pipelines?",
                ],
            },
            {
                "question": "How do you handle a situation where stakeholders want a specific result from your analysis?",
                "difficulty": "hard",
                "skills_tested": ["Ethics", "Communication"],
                "sample_answer": "Maintain objectivity. Present the data honestly. Explain methodology transparently. Suggest alternative framing if the data tells a different story. Escalate if pressured to misrepresent findings.",
                "follow_ups": [
                    "How do you handle confirmation bias in your own analysis?",
                ],
            },
        ],
        "system_design": [
            {
                "question": "Design a recommendation system for an e-commerce platform.",
                "difficulty": "hard",
                "skills_tested": ["System Design", "Machine Learning", "Scalability"],
                "sample_answer": "Collaborative filtering (user-user, item-item) + content-based filtering. Two-stage: candidate generation (fast retrieval) → ranking (ML model). Feature store for user/item features. Real-time (session-based) and batch (matrix factorization). A/B test variants. Handle cold start with popularity-based fallback.",
                "follow_ups": [
                    "How would you handle the cold start problem?",
                    "How would you evaluate recommendation quality?",
                ],
            },
            {
                "question": "Design a real-time fraud detection system for financial transactions.",
                "difficulty": "hard",
                "skills_tested": ["System Design", "Machine Learning", "Streaming"],
                "sample_answer": "Stream processing (Kafka + Flink). Feature engineering on transaction stream (velocity, amount patterns, location). Rules engine for known patterns + ML model for novel fraud. Low-latency inference (<100ms). Human-in-the-loop review. Feedback loop to retrain model. Handle class imbalance.",
                "follow_ups": [
                    "How do you handle extreme class imbalance?",
                    "How would you monitor model drift?",
                ],
            },
            {
                "question": "Design an A/B testing platform.",
                "difficulty": "medium",
                "skills_tested": ["System Design", "Statistics", "A/B Testing"],
                "sample_answer": "Experiment configuration service, randomization (hashing user IDs), event tracking pipeline, statistical analysis engine (z-test, t-test, Bayesian), guardrail metrics, sample size calculator, dashboards. Handle network effects, multiple testing correction.",
                "follow_ups": [
                    "How do you determine sample size?",
                    "How do you handle multiple comparisons?",
                ],
            },
            {
                "question": "Design a data pipeline for processing log data at scale.",
                "difficulty": "medium",
                "skills_tested": ["Data Engineering", "System Design"],
                "sample_answer": "Ingest via Kafka/Kinesis, process with Spark/Flink, store in data lake (S3/GCS) with Parquet format, query layer (Presto/Athena), orchestration (Airflow). Schema registry for evolution. Data quality checks. Monitoring and alerting.",
                "follow_ups": [
                    "How would you handle schema evolution?",
                    "How would you ensure exactly-once processing?",
                ],
            },
            {
                "question": "Design an ML model serving infrastructure.",
                "difficulty": "hard",
                "skills_tested": ["MLOps", "System Design", "Docker"],
                "sample_answer": "Model registry (MLflow), containerized inference (Docker/K8s), A/B testing with traffic splitting, feature store integration, canary deployments, latency/accuracy monitoring, auto-scaling, model versioning, rollback capability. Separate online (real-time) and batch prediction paths.",
                "follow_ups": [
                    "How would you handle model versioning and rollback?",
                    "How would you monitor for data drift?",
                ],
            },
        ],
        "coding": [
            {
                "question": "Write a function to compute the moving average of a list of numbers with a given window size.",
                "difficulty": "easy",
                "skills_tested": ["Python", "Algorithms"],
                "sample_answer": "Use a sliding window: maintain a running sum, add new element, subtract oldest when window is full. Return averages list. Time: O(n), Space: O(1) extra (excluding output).",
                "follow_ups": [
                    "How would you handle edge cases with window larger than array?",
                    "How would you implement exponential moving average?",
                ],
            },
            {
                "question": "Given a Pandas DataFrame, write code to find the top 5 customers by total purchase amount, excluding refunded orders.",
                "difficulty": "medium",
                "skills_tested": ["Pandas", "SQL", "Data Analysis"],
                "sample_answer": "df[df['status'] != 'refunded'].groupby('customer_id')['amount'].sum().nlargest(5). Filter refunds first, group by customer, sum amounts, get top 5.",
                "follow_ups": [
                    "How would you do this in SQL?",
                    "How would you handle ties?",
                ],
            },
            {
                "question": "Implement k-means clustering from scratch in Python.",
                "difficulty": "hard",
                "skills_tested": ["Machine Learning", "Python", "NumPy"],
                "sample_answer": "Initialize k centroids randomly. Iterate: (1) assign each point to nearest centroid (Euclidean distance), (2) recompute centroids as mean of assigned points. Stop when centroids don't change or max iterations reached. Use NumPy for vectorized distance computation.",
                "follow_ups": [
                    "How do you choose k?",
                    "What are the limitations of k-means?",
                ],
            },
            {
                "question": "Write a function to compute the cosine similarity between two vectors.",
                "difficulty": "easy",
                "skills_tested": ["Mathematics", "Python"],
                "sample_answer": "cosine_sim(a, b) = dot(a, b) / (norm(a) * norm(b)). Handle zero vectors. Use numpy: np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)).",
                "follow_ups": [
                    "When would cosine similarity be preferred over Euclidean distance?",
                    "How would you compute pairwise similarities for a large matrix?",
                ],
            },
            {
                "question": "Write a SQL query to find the second highest salary in each department.",
                "difficulty": "medium",
                "skills_tested": ["SQL", "Data Analysis"],
                "sample_answer": "Use DENSE_RANK() window function: SELECT department, salary FROM (SELECT *, DENSE_RANK() OVER (PARTITION BY department ORDER BY salary DESC) AS rnk FROM employees) WHERE rnk = 2.",
                "follow_ups": [
                    "What's the difference between RANK, DENSE_RANK, and ROW_NUMBER?",
                    "How would you handle ties?",
                ],
            },
        ],
    },
    # ======================================================================
    # FRONTEND DEVELOPER
    # ======================================================================
    "frontend_developer": {
        "technical": [
            {
                "question": "Explain the virtual DOM in React and why it improves performance.",
                "difficulty": "medium",
                "skills_tested": ["React", "JavaScript"],
                "sample_answer": "The virtual DOM is an in-memory representation of the real DOM. When state changes, React creates a new virtual DOM, diffs it against the previous one (reconciliation), and applies only the minimal set of changes to the real DOM. This batching reduces expensive DOM manipulations.",
                "follow_ups": [
                    "How does React's reconciliation algorithm work?",
                    "What are React Fiber and concurrent mode?",
                ],
            },
            {
                "question": "What is the difference between CSS Flexbox and Grid? When would you use each?",
                "difficulty": "easy",
                "skills_tested": ["CSS", "Responsive Design"],
                "sample_answer": "Flexbox is one-dimensional (row OR column). Grid is two-dimensional (rows AND columns). Use Flexbox for navigation bars, card layouts, centering. Use Grid for full page layouts, complex grids, dashboard layouts. They can be combined.",
                "follow_ups": [
                    "How do you handle browser compatibility for Grid?",
                    "What is the CSS gap property?",
                ],
            },
            {
                "question": "Explain closures in JavaScript and give a practical example.",
                "difficulty": "medium",
                "skills_tested": ["JavaScript"],
                "sample_answer": "A closure is a function that retains access to its lexical scope even when executed outside that scope. Example: function counter() { let count = 0; return () => ++count; }. The returned function 'closes over' the count variable. Used in data privacy, event handlers, partial application.",
                "follow_ups": [
                    "How do closures relate to the module pattern?",
                    "What are common memory leak issues with closures?",
                ],
            },
            {
                "question": "What is TypeScript's type narrowing and how does it work?",
                "difficulty": "medium",
                "skills_tested": ["TypeScript"],
                "sample_answer": "Type narrowing is TypeScript's ability to refine types within conditional blocks. Uses: typeof guards, instanceof checks, 'in' operator, discriminated unions, custom type predicates (x is Type). The compiler tracks the narrowed type within the block for type safety.",
                "follow_ups": [
                    "What are discriminated unions?",
                    "How do custom type guards work?",
                ],
            },
            {
                "question": "Explain the event loop in JavaScript. How do microtasks and macrotasks differ?",
                "difficulty": "hard",
                "skills_tested": ["JavaScript", "Browser APIs"],
                "sample_answer": "The event loop processes the call stack, then checks the microtask queue (Promises, queueMicrotask), then the macrotask queue (setTimeout, setInterval, I/O). Microtasks run before the next macrotask and before rendering. This is why Promises resolve before setTimeout(fn, 0).",
                "follow_ups": [
                    "How does requestAnimationFrame fit into the event loop?",
                    "What problems can arise from long-running microtask queues?",
                ],
            },
        ],
        "behavioral": [
            {
                "question": "How do you approach building accessible web applications?",
                "difficulty": "medium",
                "skills_tested": ["Accessibility", "HTML"],
                "sample_answer": "Follow WCAG guidelines. Use semantic HTML, ARIA attributes when needed, keyboard navigation, proper contrast ratios, screen reader testing. Include in definition of done. Use tools like Lighthouse, axe-core for automated checks.",
                "follow_ups": [
                    "What are the most common accessibility violations you've encountered?",
                    "How do you test with screen readers?",
                ],
            },
            {
                "question": "Describe your approach to code reviews for frontend code.",
                "difficulty": "easy",
                "skills_tested": ["Communication", "Teamwork"],
                "sample_answer": "Check for: correctness, readability, performance (unnecessary re-renders, bundle size), accessibility, responsive design, test coverage. Give constructive feedback with explanations. Focus on patterns, not style (use linters for that).",
                "follow_ups": [
                    "How do you handle disagreements in code reviews?",
                ],
            },
            {
                "question": "Tell me about a time you improved the performance of a web application.",
                "difficulty": "medium",
                "skills_tested": ["Performance", "Problem Solving"],
                "sample_answer": "STAR: Identified performance bottleneck (e.g., large bundle, excessive re-renders), profiled with DevTools/Lighthouse, implemented fixes (code splitting, memoization, lazy loading, image optimization), measured improvement.",
                "follow_ups": [
                    "What metrics do you use to measure frontend performance?",
                    "How do you set performance budgets?",
                ],
            },
            {
                "question": "How do you keep up with the rapidly changing frontend ecosystem?",
                "difficulty": "easy",
                "skills_tested": ["Learning Agility"],
                "sample_answer": "Follow key newsletters (JavaScript Weekly, React Status), read official documentation, attend meetups/conferences, try new tools in side projects, follow thought leaders on social media, contribute to discussions.",
                "follow_ups": [
                    "How do you decide which new frameworks or tools are worth learning?",
                ],
            },
            {
                "question": "Describe a time you had to work with a designer to implement a complex UI.",
                "difficulty": "medium",
                "skills_tested": ["Collaboration", "Communication"],
                "sample_answer": "STAR: Describe the design, how you communicated feasibility and constraints, how you iterated together, and the final result. Highlight tools used for handoff (Figma, Zeplin) and responsive considerations.",
                "follow_ups": [
                    "How do you handle situations where a design is technically difficult to implement?",
                ],
            },
        ],
        "system_design": [
            {
                "question": "Design the frontend architecture for a large-scale single-page application.",
                "difficulty": "hard",
                "skills_tested": ["System Design", "React", "Architecture"],
                "sample_answer": "Component architecture (atomic design), state management (Redux/Zustand for global, local state for components), routing (React Router), code splitting (React.lazy), API layer (fetch abstraction with caching), testing strategy (unit/integration/e2e), CI/CD, design system, error boundaries, monitoring.",
                "follow_ups": [
                    "How would you handle state management for a very large app?",
                    "What's your approach to micro-frontends?",
                ],
            },
            {
                "question": "Design a component library/design system.",
                "difficulty": "medium",
                "skills_tested": ["System Design", "React", "CSS"],
                "sample_answer": "Token-based theming (colors, spacing, typography), component hierarchy (atoms → molecules → organisms), Storybook for documentation, TypeScript props, accessibility baked in, versioning (semver), tree-shakeable exports, CSS-in-JS or CSS modules.",
                "follow_ups": [
                    "How do you handle theme customization?",
                    "How do you manage breaking changes?",
                ],
            },
            {
                "question": "Design an offline-first progressive web application.",
                "difficulty": "hard",
                "skills_tested": ["System Design", "Service Workers", "IndexedDB"],
                "sample_answer": "Service worker for caching (cache-first for static, network-first for API), IndexedDB for offline data storage, background sync for pending mutations, conflict resolution strategy (last-write-wins or merge), manifest.json for installability, push notifications.",
                "follow_ups": [
                    "How do you handle conflict resolution when syncing?",
                    "What caching strategies would you use?",
                ],
            },
            {
                "question": "Design a real-time collaborative text editor.",
                "difficulty": "hard",
                "skills_tested": ["System Design", "WebSockets", "CRDT"],
                "sample_answer": "Operational Transformation (OT) or CRDT for concurrent editing. WebSocket for real-time sync. Cursor position awareness. Undo/redo per user. Rich text model (Slate.js, ProseMirror). Server mediates transformations. Offline support with merge on reconnect.",
                "follow_ups": [
                    "What is the difference between OT and CRDT?",
                    "How would you handle large documents?",
                ],
            },
            {
                "question": "Design an image-heavy website for optimal performance.",
                "difficulty": "medium",
                "skills_tested": ["Performance", "System Design"],
                "sample_answer": "Responsive images (srcset, picture element), lazy loading (Intersection Observer), CDN with edge caching, image compression pipeline (WebP/AVIF), blur-up placeholders, infinite scroll or pagination, preconnect to image CDN, service worker caching.",
                "follow_ups": [
                    "How would you handle retina displays?",
                    "What image formats would you choose and why?",
                ],
            },
        ],
        "coding": [
            {
                "question": "Implement a debounce function in JavaScript.",
                "difficulty": "medium",
                "skills_tested": ["JavaScript", "Closures"],
                "sample_answer": "function debounce(fn, delay) { let timer; return (...args) => { clearTimeout(timer); timer = setTimeout(() => fn(...args), delay); }; }. Clears previous timer on each call, only executes after delay ms of inactivity.",
                "follow_ups": [
                    "What's the difference between debounce and throttle?",
                    "How would you add an 'immediate' option?",
                ],
            },
            {
                "question": "Write a custom React hook for fetching data with loading and error states.",
                "difficulty": "medium",
                "skills_tested": ["React", "Hooks", "TypeScript"],
                "sample_answer": "function useFetch(url) { const [data, setData] = useState(null); const [loading, setLoading] = useState(true); const [error, setError] = useState(null); useEffect(() => { fetch(url).then(r => r.json()).then(setData).catch(setError).finally(() => setLoading(false)); }, [url]); return { data, loading, error }; }. Add AbortController for cleanup.",
                "follow_ups": [
                    "How would you add caching?",
                    "How would you handle request cancellation on unmount?",
                ],
            },
            {
                "question": "Implement a function that flattens a deeply nested array.",
                "difficulty": "easy",
                "skills_tested": ["JavaScript", "Recursion"],
                "sample_answer": "function flatten(arr) { return arr.reduce((acc, item) => Array.isArray(item) ? acc.concat(flatten(item)) : acc.concat(item), []); }. Or iterative: use a stack.",
                "follow_ups": [
                    "How would you flatten to a specific depth?",
                    "What is Array.prototype.flat()?",
                ],
            },
            {
                "question": "Build a simple pub-sub (event emitter) system in JavaScript.",
                "difficulty": "medium",
                "skills_tested": ["JavaScript", "Design Patterns"],
                "sample_answer": "class EventEmitter { constructor() { this.events = {}; } on(event, fn) { (this.events[event] ||= []).push(fn); } off(event, fn) { this.events[event] = this.events[event]?.filter(f => f !== fn); } emit(event, ...args) { this.events[event]?.forEach(fn => fn(...args)); } }.",
                "follow_ups": [
                    "How would you add a 'once' method?",
                    "How would you handle errors in listeners?",
                ],
            },
            {
                "question": "Write a function to deep clone a JavaScript object, handling circular references.",
                "difficulty": "hard",
                "skills_tested": ["JavaScript", "Recursion"],
                "sample_answer": "function deepClone(obj, seen = new Map()) { if (obj === null || typeof obj !== 'object') return obj; if (seen.has(obj)) return seen.get(obj); const clone = Array.isArray(obj) ? [] : {}; seen.set(obj, clone); for (const [key, val] of Object.entries(obj)) clone[key] = deepClone(val, seen); return clone; }.",
                "follow_ups": [
                    "What about Date, RegExp, Map, Set objects?",
                    "How does structuredClone() compare?",
                ],
            },
        ],
    },
    # ======================================================================
    # BACKEND DEVELOPER
    # ======================================================================
    "backend_developer": {
        "technical": [
            {
                "question": "Explain the difference between SQL and NoSQL databases. When would you choose each?",
                "difficulty": "easy",
                "skills_tested": ["Databases", "SQL"],
                "sample_answer": "SQL: relational, ACID, structured schema, joins, vertical scaling. Best for transactional data, complex queries. NoSQL: flexible schema (document/key-value/graph/column), eventual consistency, horizontal scaling. Best for unstructured data, high write throughput, rapid iteration.",
                "follow_ups": [
                    "What is CAP theorem?",
                    "Can you use SQL and NoSQL together?",
                ],
            },
            {
                "question": "What are database indexes and how do they improve query performance?",
                "difficulty": "medium",
                "skills_tested": ["Databases", "SQL", "Performance"],
                "sample_answer": "Indexes are data structures (typically B-tree or hash) that speed up data retrieval by avoiding full table scans. Trade-off: faster reads but slower writes (index must be updated). Types: single-column, composite, unique, partial, full-text. Use EXPLAIN to analyze query plans.",
                "follow_ups": [
                    "When should you NOT add an index?",
                    "What is a covering index?",
                ],
            },
            {
                "question": "Explain REST API design best practices.",
                "difficulty": "medium",
                "skills_tested": ["REST APIs", "HTTP"],
                "sample_answer": "Use nouns for resources (/users), HTTP verbs for actions (GET/POST/PUT/DELETE), proper status codes (200/201/400/404/500), pagination, versioning (/v1/), HATEOAS, consistent error format, authentication (JWT/OAuth), rate limiting, documentation (OpenAPI).",
                "follow_ups": [
                    "What's the difference between PUT and PATCH?",
                    "How does GraphQL compare to REST?",
                ],
            },
            {
                "question": "What is the N+1 query problem and how do you solve it?",
                "difficulty": "medium",
                "skills_tested": ["Databases", "ORM", "Performance"],
                "sample_answer": "N+1 occurs when fetching a list of N items and then making a separate query for each item's related data (1 + N queries). Solutions: eager loading (JOIN/selectinload), batch loading, DataLoader pattern. In SQLAlchemy: use joinedload() or selectinload() in queries.",
                "follow_ups": [
                    "How do you detect N+1 queries in production?",
                    "What are the trade-offs of eager vs lazy loading?",
                ],
            },
            {
                "question": "Explain JWT authentication. What are its advantages and security considerations?",
                "difficulty": "medium",
                "skills_tested": ["Security", "REST APIs"],
                "sample_answer": "JWT (JSON Web Token) is a self-contained token with header.payload.signature. Advantages: stateless (no server-side sessions), scalable, cross-domain. Security: use HTTPS, short expiration, refresh tokens, store in httpOnly cookies (not localStorage), validate signature, check expiry.",
                "follow_ups": [
                    "How do you handle token revocation?",
                    "What is the difference between symmetric and asymmetric JWT signing?",
                ],
            },
        ],
        "behavioral": [
            {
                "question": "Tell me about a time you had to make a significant architectural decision.",
                "difficulty": "medium",
                "skills_tested": ["Decision Making", "Communication"],
                "sample_answer": "STAR: Describe the context, options considered, criteria for decision (scalability, team expertise, timeline), how you gathered input, the decision made, and the outcome.",
                "follow_ups": [
                    "How do you document architectural decisions?",
                    "How do you handle technical debt from past decisions?",
                ],
            },
            {
                "question": "How do you approach a legacy codebase that needs modernization?",
                "difficulty": "medium",
                "skills_tested": ["Problem Solving", "Strategic Thinking"],
                "sample_answer": "Understand first (read code, talk to team), add tests before changing, strangler fig pattern (incrementally replace), identify highest-risk areas, establish coding standards, improve CI/CD, communicate plan with stakeholders, avoid big rewrites.",
                "follow_ups": [
                    "How do you convince stakeholders to invest in modernization?",
                    "What metrics do you use to track progress?",
                ],
            },
            {
                "question": "Describe a time you improved the reliability of a system.",
                "difficulty": "medium",
                "skills_tested": ["Reliability", "Problem Solving"],
                "sample_answer": "STAR: Identified reliability issues (error rates, downtime), implemented improvements (monitoring, alerting, circuit breakers, retries, health checks), measured impact (reduced error rate by X%, improved uptime).",
                "follow_ups": [
                    "What monitoring tools do you prefer?",
                    "How do you conduct post-mortems?",
                ],
            },
            {
                "question": "How do you ensure your APIs are well-documented and easy to use?",
                "difficulty": "easy",
                "skills_tested": ["Communication", "Documentation"],
                "sample_answer": "Use OpenAPI/Swagger for auto-generated docs. Write clear descriptions, provide examples. Include error codes and their meanings. Maintain a changelog. Get feedback from consumers. Keep docs in sync with code (doc-as-code).",
                "follow_ups": [
                    "How do you handle API versioning?",
                ],
            },
            {
                "question": "Tell me about handling a security vulnerability in production.",
                "difficulty": "hard",
                "skills_tested": ["Security", "Incident Response"],
                "sample_answer": "STAR: Discovery (audit, report, scan), assessment (severity, impact), containment (immediate mitigation), fix (patch, test, deploy), communication (stakeholders, users if needed), post-mortem (root cause, prevention).",
                "follow_ups": [
                    "How do you proactively prevent security vulnerabilities?",
                ],
            },
        ],
        "system_design": [
            {
                "question": "Design a scalable REST API for an e-commerce platform.",
                "difficulty": "hard",
                "skills_tested": ["System Design", "REST APIs", "Databases"],
                "sample_answer": "Microservices: product catalog, user, order, payment, inventory. API gateway for routing/auth/rate-limiting. Relational DB for orders (ACID), NoSQL for catalog (flexible schema). Caching (Redis) for hot data. Message queue for async operations (order processing). Search with Elasticsearch.",
                "follow_ups": [
                    "How would you handle distributed transactions?",
                    "How would you implement search and filtering?",
                ],
            },
            {
                "question": "Design a task queue / job processing system.",
                "difficulty": "medium",
                "skills_tested": ["System Design", "Message Queues", "Reliability"],
                "sample_answer": "Producer-consumer pattern. Queue (Redis/SQS/RabbitMQ) stores jobs. Workers poll/subscribe. Features: priority queues, retry with exponential backoff, dead letter queue, idempotency keys, progress tracking, scheduling, horizontal worker scaling. Monitoring: queue depth, processing time, failure rate.",
                "follow_ups": [
                    "How do you ensure at-least-once processing?",
                    "How do you handle poison messages?",
                ],
            },
            {
                "question": "Design a caching strategy for a high-traffic API.",
                "difficulty": "medium",
                "skills_tested": ["System Design", "Caching", "Performance"],
                "sample_answer": "Multi-layer: CDN for static content, application cache (Redis/Memcached) for computed results, DB query cache. Cache invalidation strategies: TTL, event-driven, write-through. Cache-aside pattern for reads. Handle thundering herd with lock/singleflight. Monitor hit rates.",
                "follow_ups": [
                    "How do you handle cache invalidation?",
                    "What is the thundering herd problem?",
                ],
            },
            {
                "question": "Design an authentication and authorization system.",
                "difficulty": "medium",
                "skills_tested": ["Security", "System Design"],
                "sample_answer": "Authentication: OAuth 2.0 / OpenID Connect, JWT access + refresh tokens. Authorization: RBAC (Role-Based Access Control) or ABAC. Centralized auth service. Token storage (httpOnly cookies). Rate limiting on login. MFA support. Session management. Audit logging.",
                "follow_ups": [
                    "How would you implement fine-grained permissions?",
                    "How does OAuth 2.0 work?",
                ],
            },
            {
                "question": "Design a logging and monitoring infrastructure for microservices.",
                "difficulty": "medium",
                "skills_tested": ["System Design", "Monitoring", "DevOps"],
                "sample_answer": "Structured logging (JSON) with correlation IDs. Centralized log aggregation (ELK stack / Loki). Metrics (Prometheus + Grafana): latency, error rate, throughput (RED method). Distributed tracing (Jaeger/Zipkin). Alerting with escalation. Dashboards per service and system-wide.",
                "follow_ups": [
                    "How do you implement distributed tracing?",
                    "What alerts would you set up first?",
                ],
            },
        ],
        "coding": [
            {
                "question": "Write a middleware function for a web framework that logs request duration and returns it as a response header.",
                "difficulty": "easy",
                "skills_tested": ["Python", "REST APIs", "Middleware"],
                "sample_answer": "async def timing_middleware(request, call_next): start = time.time(); response = await call_next(request); duration = time.time() - start; response.headers['X-Response-Time'] = f'{duration:.4f}s'; logger.info(f'{request.method} {request.url.path} {duration:.4f}s'); return response.",
                "follow_ups": [
                    "How would you add request ID tracking?",
                    "How would you handle exceptions in middleware?",
                ],
            },
            {
                "question": "Implement a simple rate limiter using a sliding window algorithm.",
                "difficulty": "medium",
                "skills_tested": ["Algorithms", "Python", "System Design"],
                "sample_answer": "Track timestamps of requests in a deque/list per key. On new request: remove timestamps older than window. If count < limit, allow and add timestamp. Otherwise reject. For production: use Redis ZSET with ZRANGEBYSCORE for atomic sliding window.",
                "follow_ups": [
                    "How would you make this distributed?",
                    "What are the trade-offs vs token bucket?",
                ],
            },
            {
                "question": "Write a function to validate and parse a nested JSON configuration, returning typed errors for invalid fields.",
                "difficulty": "medium",
                "skills_tested": ["Python", "Data Validation"],
                "sample_answer": "Use Pydantic: define a BaseModel with typed fields, validators, and Optional fields with defaults. Parse with model_validate(json_data). Catch ValidationError and return structured error messages with field paths.",
                "follow_ups": [
                    "How would you handle environment-specific overrides?",
                    "How do you version configurations?",
                ],
            },
            {
                "question": "Implement a retry decorator with exponential backoff and jitter.",
                "difficulty": "medium",
                "skills_tested": ["Python", "Reliability", "Decorators"],
                "sample_answer": "def retry(max_retries=3, base_delay=1): def decorator(fn): @wraps(fn) async def wrapper(*args, **kwargs): for attempt in range(max_retries): try: return await fn(*args, **kwargs) except Exception: if attempt == max_retries-1: raise; delay = base_delay * 2**attempt + random.uniform(0, 1); await asyncio.sleep(delay) return wrapper; return decorator.",
                "follow_ups": [
                    "How would you add specific exception filtering?",
                    "What is jitter and why is it important?",
                ],
            },
            {
                "question": "Write an async function to fetch multiple URLs concurrently and return results as they complete.",
                "difficulty": "medium",
                "skills_tested": ["Python", "Async", "HTTP"],
                "sample_answer": "async def fetch_all(urls): async with httpx.AsyncClient() as client: tasks = [client.get(url) for url in urls]; results = await asyncio.gather(*tasks, return_exceptions=True); return [(url, r) for url, r in zip(urls, results)]. Or use asyncio.as_completed for streaming results.",
                "follow_ups": [
                    "How would you limit concurrency?",
                    "How would you handle timeouts per request?",
                ],
            },
        ],
    },
}

# ---------------------------------------------------------------------------
# Keyword maps for deterministic evaluation
# ---------------------------------------------------------------------------

_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "technical": [
        "algorithm", "data structure", "complexity", "time", "space", "O(n)",
        "O(1)", "O(log n)", "hash", "tree", "graph", "stack", "queue",
        "array", "linked list", "database", "index", "query", "cache",
        "memory", "thread", "process", "async", "sync", "API", "REST",
        "HTTP", "TCP", "protocol", "framework", "library", "pattern",
        "design", "architecture", "class", "object", "function", "module",
        "interface", "abstract", "inheritance", "polymorphism", "encapsulation",
        "type", "compile", "runtime", "garbage collection", "reference",
    ],
    "behavioral": [
        "team", "collaborate", "communication", "stakeholder", "deadline",
        "prioritize", "conflict", "feedback", "mentor", "lead", "challenge",
        "learn", "adapt", "improve", "process", "decision", "impact",
        "result", "outcome", "measure", "success", "failure", "mistake",
        "growth", "responsibility", "initiative", "proactive",
    ],
    "system_design": [
        "scalability", "scale", "horizontal", "vertical", "load balancer",
        "cache", "CDN", "database", "sharding", "replication", "partition",
        "microservice", "monolith", "API gateway", "message queue", "kafka",
        "redis", "queue", "async", "event", "consistency", "availability",
        "fault tolerance", "redundancy", "monitoring", "latency", "throughput",
        "CAP", "ACID", "eventual consistency", "circuit breaker",
    ],
    "coding": [
        "time complexity", "space complexity", "O(n)", "O(1)", "edge case",
        "test", "boundary", "loop", "recursive", "iterative", "pointer",
        "index", "sort", "search", "traverse", "return", "variable",
        "condition", "implementation", "solution", "approach", "optimize",
    ],
}


def _tokenize_response(text: str) -> set[str]:
    """Tokenize a response into lowercase words."""
    return set(re.findall(r"[a-z][a-z0-9_/#+.]*", text.lower()))


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class InterviewEngine:
    """Interview preparation and evaluation engine."""

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def generate_session(
        self,
        role: str,
        skills: list[str] | None = None,
        session_type: str = "technical",
        count: int = 5,
    ) -> dict[str, Any]:
        """Generate an interview session synchronously, returning a dictionary."""
        role_key = role.lower().replace(" ", "_").replace("-", "_")
        bank = QUESTION_BANK.get(role_key) or QUESTION_BANK.get("software_engineer", {})
        
        questions: list[Question] = []
        seen_texts: set[str] = set()

        if session_type != "mixed":
            # STRICT MODE: Only include questions that match the chosen format!
            # 1. First, take from the user's selected role in this format
            for item in bank.get(session_type, []):
                if item["question"] not in seen_texts:
                    seen_texts.add(item["question"])
                    questions.append(Question(
                        question=item["question"],
                        category=session_type,
                        difficulty=item.get("difficulty", "medium"),
                        role=role,
                        skills_tested=item.get("skills_tested", []),
                        sample_answer=item.get("sample_answer", ""),
                        follow_ups=item.get("follow_ups", []),
                    ))
                if len(questions) >= count:
                    break

            # 2. If user requests more, take from other roles strictly in THIS SAME format
            if len(questions) < count:
                for other_role, other_bank in QUESTION_BANK.items():
                    if other_role == role_key:
                        continue
                    for item in other_bank.get(session_type, []):
                        if item["question"] not in seen_texts:
                            seen_texts.add(item["question"])
                            questions.append(Question(
                                question=item["question"],
                                category=session_type,
                                difficulty=item.get("difficulty", "medium"),
                                role=role,
                                skills_tested=item.get("skills_tested", []),
                                sample_answer=item.get("sample_answer", ""),
                                follow_ups=item.get("follow_ups", []),
                            ))
                        if len(questions) >= count:
                            break
                    if len(questions) >= count:
                        break
        else:
            # MIXED MODE: Can take from all categories
            for cat in bank.keys():
                for item in bank.get(cat, []):
                    if item["question"] not in seen_texts:
                        seen_texts.add(item["question"])
                        questions.append(Question(
                            question=item["question"],
                            category=cat,
                            difficulty=item.get("difficulty", "medium"),
                            role=role,
                            skills_tested=item.get("skills_tested", []),
                            sample_answer=item.get("sample_answer", ""),
                            follow_ups=item.get("follow_ups", []),
                        ))
                    if len(questions) >= count:
                        break
                if len(questions) >= count:
                    break

            if len(questions) < count:
                for other_role, other_bank in QUESTION_BANK.items():
                    if other_role == role_key:
                        continue
                    for cat, items in other_bank.items():
                        for item in items:
                            if item["question"] not in seen_texts:
                                seen_texts.add(item["question"])
                                questions.append(Question(
                                    question=item["question"],
                                    category=cat,
                                    difficulty=item.get("difficulty", "medium"),
                                    role=role,
                                    skills_tested=item.get("skills_tested", []),
                                    sample_answer=item.get("sample_answer", ""),
                                    follow_ups=item.get("follow_ups", []),
                                ))
                            if len(questions) >= count:
                                break
                        if len(questions) >= count:
                            break
                    if len(questions) >= count:
                        break
        
        session = InterviewSession(
            candidate_id=1,
            session_type=session_type,
            questions=questions[:count],
        )
        return session.model_dump()

    async def start_session(
        self,
        candidate_id: int,
        job_id: int | None = None,
        session_type: str = "technical",
        role: str = "software_engineer",
    ) -> InterviewSession:
        """Create a new interview session with generated questions.

        Parameters
        ----------
        candidate_id:
            ID of the candidate.
        job_id:
            Optional job ID to tailor questions.
        session_type:
            One of: technical, behavioral, system_design, coding, mixed.
        role:
            Target role key.
        """
        role_key = role.lower().replace(" ", "_").replace("-", "_")

        # Load skills from job if possible
        skills: list[str] = []
        if job_id is not None:
            skills = await self._load_job_skills(job_id)

        questions = await self.generate_questions(
            role=role_key,
            skills=skills,
            session_type=session_type,
            count=5,
        )

        return InterviewSession(
            candidate_id=candidate_id,
            job_id=job_id,
            session_type=session_type,
            questions=questions,
        )

    # ------------------------------------------------------------------
    # Question generation
    # ------------------------------------------------------------------

    async def generate_questions(
        self,
        role: str,
        skills: list[str] | None = None,
        session_type: str = "technical",
        count: int = 5,
    ) -> list[Question]:
        """Generate interview questions from the question bank.

        Parameters
        ----------
        role:
            Role key (e.g. ``"software_engineer"``).
        skills:
            Optional list of skills to prioritize questions for.
        session_type:
            Category or ``"mixed"`` for all categories.
        count:
            Number of questions to generate.
        """
        role_key = role.lower().replace(" ", "_").replace("-", "_")
        bank = QUESTION_BANK.get(role_key)

        if not bank:
            # Fallback to software_engineer bank
            bank = QUESTION_BANK.get("software_engineer", {})
            logger.info(
                "No question bank for role '%s'; falling back to software_engineer.",
                role_key,
            )

        # Determine categories
        if session_type == "mixed":
            categories = list(bank.keys())
        else:
            categories = [session_type] if session_type in bank else list(bank.keys())

        # Gather candidate questions
        candidates: list[dict[str, Any]] = []
        for cat in categories:
            for q in bank.get(cat, []):
                candidates.append({**q, "category": cat, "role": role_key})

        # Score questions by skill relevance
        if skills:
            skill_set = {s.lower() for s in skills}
            candidates.sort(
                key=lambda q: -len(
                    {s.lower() for s in q.get("skills_tested", [])} & skill_set
                )
            )

        # Ensure difficulty spread
        selected: list[dict[str, Any]] = []
        seen_questions: set[str] = set()

        # First pass: pick by difficulty spread
        for difficulty in ("easy", "medium", "hard"):
            for q in candidates:
                if (
                    q["question"] not in seen_questions
                    and q.get("difficulty") == difficulty
                    and len(selected) < count
                ):
                    selected.append(q)
                    seen_questions.add(q["question"])

        # Fill remaining
        for q in candidates:
            if q["question"] not in seen_questions and len(selected) < count:
                selected.append(q)
                seen_questions.add(q["question"])

        selected = selected[:count]

        return [
            Question(
                question=q["question"],
                category=q["category"],
                difficulty=q.get("difficulty", "medium"),
                role=q.get("role", role_key),
                skills_tested=q.get("skills_tested", []),
                sample_answer=q.get("sample_answer", ""),
                follow_ups=q.get("follow_ups", []),
            )
            for q in selected
        ]

    # ------------------------------------------------------------------
    # Response evaluation
    # ------------------------------------------------------------------

    async def evaluate_response(
        self, question: dict[str, Any], response: str
    ) -> Evaluation:
        """Evaluate a candidate's answer to an interview question.

        Uses deterministic keyword/coverage scoring. Attempts LLM-enhanced
        evaluation when available.

        Parameters
        ----------
        question:
            The question dict (must have ``id``, ``question``, ``category``,
            ``sample_answer``).
        response:
            The candidate's answer text.
        """
        question_id = question.get("id", "unknown")
        category = question.get("category", "technical")
        sample_answer = question.get("sample_answer", "")
        question_text = question.get("question", "")

        # Deterministic scoring
        score, strengths, improvements = self._score_deterministic(
            response=response,
            sample_answer=sample_answer,
            category=category,
        )

        feedback = self._generate_feedback(score, strengths, improvements)

        # Try LLM-enhanced evaluation
        llm_eval = await self._try_llm_evaluation(question_text, response, sample_answer)
        if llm_eval is not None:
            # Blend deterministic and LLM scores
            score = score * 0.4 + llm_eval["score"] * 0.6
            if llm_eval.get("feedback"):
                feedback = llm_eval["feedback"]
            strengths = llm_eval.get("strengths", strengths)
            improvements = llm_eval.get("improvements", improvements)

        return Evaluation(
            question_id=question_id,
            score=round(min(100.0, max(0.0, score)), 2),
            feedback=feedback,
            strengths=strengths,
            areas_for_improvement=improvements,
            model_answer=sample_answer,
        )

    # ------------------------------------------------------------------
    # Deterministic scoring
    # ------------------------------------------------------------------

    def _score_deterministic(
        self,
        response: str,
        sample_answer: str,
        category: str,
    ) -> tuple[float, list[str], list[str]]:
        """Score response using keyword matching and coverage."""
        if not response or not response.strip():
            return (
                0.0,
                [],
                ["No response provided. Please provide a detailed answer."],
            )

        response_tokens = _tokenize_response(response)
        strengths: list[str] = []
        improvements: list[str] = []

        # 1. Length adequacy (0-20 points)
        word_count = len(response.split())
        if word_count >= 100:
            length_score = 20.0
            strengths.append("Detailed and thorough response")
        elif word_count >= 50:
            length_score = 15.0
        elif word_count >= 25:
            length_score = 10.0
            improvements.append("Consider providing more detail and examples")
        else:
            length_score = 5.0
            improvements.append("Response is too brief. Elaborate with examples and reasoning")

        # 2. Sample answer coverage (0-40 points)
        if sample_answer:
            sample_tokens = _tokenize_response(sample_answer)
            if sample_tokens:
                overlap = len(response_tokens & sample_tokens) / len(sample_tokens)
                coverage_score = overlap * 40.0
                if overlap >= 0.5:
                    strengths.append("Good coverage of key concepts")
                elif overlap >= 0.25:
                    strengths.append("Covers some relevant concepts")
                else:
                    improvements.append(
                        "Consider addressing more key points from the expected answer"
                    )
            else:
                coverage_score = 20.0  # neutral
        else:
            coverage_score = 20.0

        # 3. Category keyword relevance (0-20 points)
        category_kws = _CATEGORY_KEYWORDS.get(category, [])
        if category_kws:
            kw_set = {kw.lower() for kw in category_kws}
            # Check multi-word keywords
            response_lower = response.lower()
            kw_matches = sum(
                1 for kw in kw_set if kw in response_lower
            )
            kw_ratio = kw_matches / len(kw_set) if kw_set else 0
            keyword_score = min(20.0, kw_ratio * 60.0)  # scaled

            if kw_ratio >= 0.15:
                strengths.append("Uses appropriate technical vocabulary")
            else:
                improvements.append("Use more domain-specific terminology")
        else:
            keyword_score = 10.0

        # 4. Structure and clarity (0-20 points)
        structure_score = 0.0

        # Check for structured answer (bullet points, numbered lists, paragraphs)
        has_structure = any(
            indicator in response
            for indicator in ("\n", "- ", "* ", "1.", "2.", ". ", "first", "second")
        )
        if has_structure:
            structure_score += 10.0
            strengths.append("Well-structured response")
        else:
            improvements.append(
                "Consider structuring your answer with clear sections or bullet points"
            )

        # Check for examples
        has_examples = any(
            kw in response.lower()
            for kw in ("example", "for instance", "such as", "e.g.", "like", "consider")
        )
        if has_examples:
            structure_score += 10.0
            strengths.append("Provides concrete examples")
        else:
            improvements.append("Include specific examples to strengthen your answer")

        total = length_score + coverage_score + keyword_score + structure_score

        return total, strengths, improvements

    @staticmethod
    def _generate_feedback(
        score: float, strengths: list[str], improvements: list[str]
    ) -> str:
        """Generate human-readable feedback from score and analysis."""
        if score >= 80:
            opening = "Excellent answer!"
        elif score >= 60:
            opening = "Good answer with room for improvement."
        elif score >= 40:
            opening = "Adequate answer, but could be strengthened significantly."
        elif score >= 20:
            opening = "The answer needs more depth and detail."
        else:
            opening = "The answer is insufficient. Please review the topic and try again."

        parts = [opening]
        if strengths:
            parts.append(f"Strengths: {'; '.join(strengths)}.")
        if improvements:
            parts.append(f"Areas to improve: {'; '.join(improvements)}.")

        return " ".join(parts)

    # ------------------------------------------------------------------
    # LLM-enhanced evaluation (optional)
    # ------------------------------------------------------------------

    @staticmethod
    async def _try_llm_evaluation(
        question: str, response: str, sample_answer: str
    ) -> dict[str, Any] | None:
        """Attempt LLM-based evaluation. Returns None if unavailable."""
        try:
            from app.services.llm.llm_service import LLMService  # type: ignore[import-untyped]

            llm = LLMService()
            prompt = (
                "You are an expert interviewer. Evaluate this interview response.\n\n"
                f"Question: {question}\n\n"
                f"Candidate's Response: {response}\n\n"
                f"Reference Answer: {sample_answer}\n\n"
                "Provide your evaluation in this exact format:\n"
                "SCORE: <number 0-100>\n"
                "FEEDBACK: <one paragraph>\n"
                "STRENGTHS: <comma-separated list>\n"
                "IMPROVEMENTS: <comma-separated list>"
            )

            result = await llm.generate(prompt)
            if not result:
                return None

            # Parse structured response
            parsed: dict[str, Any] = {}
            for line in result.strip().split("\n"):
                line = line.strip()
                if line.startswith("SCORE:"):
                    try:
                        parsed["score"] = float(
                            re.search(r"[\d.]+", line.split(":", 1)[1]).group()  # type: ignore[union-attr]
                        )
                    except (ValueError, AttributeError):
                        pass
                elif line.startswith("FEEDBACK:"):
                    parsed["feedback"] = line.split(":", 1)[1].strip()
                elif line.startswith("STRENGTHS:"):
                    parsed["strengths"] = [
                        s.strip()
                        for s in line.split(":", 1)[1].split(",")
                        if s.strip()
                    ]
                elif line.startswith("IMPROVEMENTS:"):
                    parsed["improvements"] = [
                        s.strip()
                        for s in line.split(":", 1)[1].split(",")
                        if s.strip()
                    ]

            if "score" in parsed:
                return parsed

        except Exception:
            logger.debug("LLM evaluation unavailable; using deterministic scoring.")

        return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    async def _load_job_skills(job_id: int) -> list[str]:
        """Try to load skills from a job posting in the database."""
        try:
            from app.core.database import async_session  # type: ignore[import-untyped]
            from app.models.models import Job  # type: ignore[import-untyped]
            from sqlalchemy import select

            async with async_session() as session:
                stmt = select(Job).where(Job.id == job_id)
                result = await session.execute(stmt)
                job = result.scalar_one_or_none()
                if job and hasattr(job, "required_skills"):
                    skills = job.required_skills
                    if isinstance(skills, list):
                        return skills
                    if isinstance(skills, str):
                        import json

                        try:
                            parsed = json.loads(skills)
                            if isinstance(parsed, list):
                                return parsed
                        except (json.JSONDecodeError, TypeError):
                            return [s.strip() for s in skills.split(",") if s.strip()]
        except Exception:
            logger.debug("Could not load job skills from database.")

        return []
