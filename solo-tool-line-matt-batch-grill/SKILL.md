---
name: solo-tool-line-matt-batch-grill
description: 【手动点名】"高强度连环追问：把一个计划或方案的所有待决策点整理成一棵决策树，每一轮把当前已能回答的问题一次性全部列出（每题附推荐答案），你答完一轮，再根据答案生成下一轮，直到没有任何被默默假设的问题。适合动手前把边界情况、依赖决策一口气问清；AI 自己能查到的资料不会来问你，只把需要你拍板的决策拿给你。"
disable-model-invocation: true
---

Interview the user relentlessly until you reach a shared understanding. Map this as a **design tree**: every decision branches into the decisions that hang off it.

Work the tree in **rounds**. The **frontier** is every decision whose prerequisites are already settled — the questions you can ask *now* without guessing at answers you haven't heard yet. Ask the whole frontier in one round: number each question and give your recommended answer. Then wait for the user's answers before the next round.

Each round the user answers reshapes the tree — settled decisions push the frontier outward and unblock questions that depended on them. Recompute the frontier and ask the next round. A question whose answer depends on another question still open in this round belongs to a *later* round, not this one.

Finding *facts* is your job, never the user's. When a frontier question needs a fact from the environment (filesystem, tools, etc.), dispatch a sub-agent to find it — don't ask the user for anything you could look up yourself. Don't block on it: a running exploration is an unsettled prerequisite, so only the questions downstream of it wait for the sub-agent to report — ask the rest of the frontier now. The *decisions* are the user's — put each to them and wait.

The session is done when the frontier is empty: every branch of the design tree visited, nothing left silently assumed. Do not act on it until the user confirms you have reached a shared understanding.
