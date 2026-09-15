# Streamlining E-commerce Customer Service with AI Chatbots using Prompt Engineering

## Business Problem

An e-commerce company is facing challenges in handling a high volume of customer inquiries daily. This has resulted in increased wait times, customer dissatisfaction, and inefficient use of customer service resources. The company seeks to improve response efficiency and customer satisfaction while reducing operational costs.

## Objective

Develop an AI-powered chatbot that can handle routine customer inquiries, automate responses, and deliver personalized customer experiences. The chatbot should proactively understand customer sentiment and context to provide relevant and appropriate responses.

## Project Scope

1. Identify opportunities for automation and define the RAG and golden datasets.
2. Design AI agent(s) to handle customer inquiries and use an LLM-as-a-Judge for response evaluation.
3. Integrate a live tool to automatically document customer conversations.
4. Implement system-level guardrails to protect against prompt injection and other attacks.
5. Define evaluation metrics, testing strategy, and validate the chatbot's performance.
6. Share the agent and datasets as part of the final submission.

## Expected Outcome

An AI-powered e-commerce customer service chatbot that improves response efficiency, reduces operational costs, and delivers accurate, secure, and personalized customer support.

## Install Chatcom Customer Support Plugin

This repository is also a GitHub Copilot plugin marketplace. Add the marketplace and install the Chatcom Customer Support plugin with:

```bash
copilot plugin marketplace add https://github.com/raj-rvd5256/ChatCom.git
copilot plugin install chatcom-customer-support@chatcom-marketplace
```

The local executable adapter requires Python and the dependencies listed in `requirements.txt`. Conversation documentation is written to a local Excel workbook; it is not a Microsoft 365 or SharePoint integration.
