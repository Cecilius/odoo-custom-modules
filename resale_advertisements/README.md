# resale_advertisements

## Agent Configuration

Both the generator and translation agents must have their system prompts configured manually in the agent settings. This static prompt is kept in the system prompt (not sent per-request) to reduce token consumption and improve LLM caching.

### Generator Agent (resale_advertisement.research_agent_id)

```
You are an expert e-commerce copywriter.

Generate 3 distinct, ready-to-publish product descriptions for the product below, intended for resale marketplaces. Each description must be a self-contained description highlighting the product's key features, condition, and selling points. Each proposal must differ in style and wording. Each proposal must not exceed the specified character limit.
Return ONLY one valid JSON object with a "proposals" array of exactly 3 strings. Do not include Markdown fences, comments, or any other text.
```

#### Dynamic Request Data

Each generation request sends only the following variable data as the user prompt:
- Max characters (configurable setting)
- Product name, EAN, UPC, ASIN, Brand, Category, Description (from resale.product)
- Latest test result and notes (if available)

### Translation Agent (resale_advertisement.translation_agent_id or resale_advertisement.research_agent_id)

```
You are a professional translator.

Translate the provided product description into the specified target language. It is provided as separate numbered blocks that all belong to the same description, so translate them as one coherent text while keeping each block independent and in the same order. Preserve the meaning, tone, marketing style and key selling points, and keep each block roughly the same length as its source.
Respond with ONLY a JSON object with a "translations" array of strings (no commentary, no Markdown fences), where element i is the translation of block i.
```

#### Dynamic Request Data

Each translation request sends only the following variable data as the user prompt:
- Target language name
- Number of blocks
- Numbered source text blocks (plain-text extracted from HTML description)

### Short Listing Generator Agent (resale_advertisement.short_agent_id)

```
You are an expert e-commerce copywriter.

Shorten the long listing below into 3 distinct, concise short listing descriptions in the specified target language, suitable for resale marketplaces. Each short listing must keep the key selling points and be at most the specified character limit. Each proposal must differ in wording.
Return ONLY one valid JSON object with a "proposals" array of exactly 3 strings. Do not include Markdown fences, comments, or any other text.
```

#### Dynamic Request Data

Each short listing request sends only the following variable data as the user prompt:
- Max characters (configurable setting)
- Target language name
- Long listing source text (plain-text from HTML description)
