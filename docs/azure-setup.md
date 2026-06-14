# Azure / Foundry IQ setup (optional — for Azure mode)

TaxMind runs fully without Azure. Follow this to enable the real Foundry IQ +
Azure OpenAI path. Everything fits inside the **$200 Azure free credit**.

> Use a **personal** Microsoft account (not a corporate tenant). Keep your `.env`
> out of git — it is already git-ignored. A leaked Azure key gets drained fast.

## 1. Account & resource group
- Sign up at https://azure.microsoft.com/free (card for verification only; keep the
  spending limit **ON**).
- Create a resource group `taxmind-rg`. Pick an AI-capable region in this order:
  **East US 2 → Sweden Central → Switzerland North** (avoid India regions for AI).

## 2. Azure OpenAI
- Create an Azure OpenAI resource (Standard S0). Open the **Foundry portal**.
- Deploy two models: `gpt-4o-mini` (dev, name `gpt-4o-mini-dev`) and `gpt-4o`
  (demo, name `gpt-4o-demo`).
- If a deployment fails with "no capacity", try the next region. Fallback:
  `gpt-35-turbo`.
- Save `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_KEY`, deployment names to `.env`.

## 3. Azure AI Search (backs Foundry IQ)
- Create "Azure AI Search", tier **Free (F)** (1 free instance per subscription;
  else Basic). Save `AZURE_SEARCH_ENDPOINT`, `AZURE_SEARCH_KEY`.

## 4. Foundry IQ knowledge base
- In the Foundry portal (https://ai.azure.com) create a project `taxmind-foundry`.
- Knowledge → Create knowledge base → Foundry IQ; connect your AI Search resource.
- Add a knowledge source: **Azure Blob** → container `gst-knowledge`.
- Save `FOUNDRY_IQ_ENDPOINT`, `FOUNDRY_IQ_KNOWLEDGE_BASE`.

## 5. Blob storage
- Create a Standard LRS storage account; containers `uploads` and `gst-knowledge`.
- Save `AZURE_STORAGE_CONNECTION_STRING`.

## 6. Wire it up
```bash
cp .env.example .env          # then fill in the values above
python scripts/smoke_test.py  # confirm OpenAI + Search are alive
python scripts/setup_foundry_iq.py   # upload GST docs + verify cited retrieval
python scripts/run_full_pipeline.py  # header should now read mode: AZURE
```

## Cost guardrails
- Set a budget alert (Cost Management → Budgets) at $50/$100/$150.
- Expected hackathon spend: well under $30 of the $200 credit.
- API versions used: Azure OpenAI `2024-08-01-preview`; Foundry IQ agentic
  retrieval `2026-05-01-preview`.
