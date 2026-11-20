# Judging

Teams have up to 3 people. Solo projects are welcome. Get the submission link from event staff.

| Criterion | Weight | What to show |
|---|---|---|
| Other Akamai Cloud services | 40% | Services a useful feature depends on, why they fit, and how you connected them |
| Inference | 20% | A useful model task, why you chose the model, and how you checked its results |
| Usefulness | 20% | Who needs the app, how they use it, and why it helps |
| Creativity | 20% | What is different about your approach and why that makes it better |

More services do not automatically mean a higher score. Choose what your app needs and use it well.

Your event key works with three models, listed in [Lab 01](../01-inference/README.md#models). You can use another provider instead. That project does not earn the 20% for inference, but it can still win.

## Prepare your demo

1. Name the user and the task.
2. Show the task working from input to result.
3. Show how the app uses each service. Be ready to explain the code or settings.
4. Explain a choice about speed, reliability, access, or growth where it matters.
5. Describe what you checked and what still does not work.

A resource shown in Cloud Manager is not enough on its own. Show the feature that uses it. Check model answers against known results, including an input the model cannot answer.

<details><summary>Example: the volunteer handbook app</summary>

Object Storage keeps the handbook the app reads. A key limited to that bucket keeps other buckets out of reach. PostgreSQL saves answers so the next volunteer can see what was discussed. The demo shows a question answered from the file and history that remains after the app restarts.

Explain the need for each service in your own project.
</details>

## Put this in your README

```text
User and task: [who needs this, and what they need to do]
Benefit: [why they would use the app]
Services: [what each service does, and why it fits]
Inference: [model, task, reason for choosing it, and how we checked it]
Technical choice: [a decision about speed, reliability, access, or growth]
Our idea: [what is different, and why it helps]
Demo: [input, steps, and result]
Known limits: [what does not work yet]
```

Use the [service guide](services.md) to choose your next lab. Follow the organizers' official rules if they differ from this page.
