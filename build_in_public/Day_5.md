# Day 5

The aim of today is to generate a synthetic dataset of 200 question, document pairs.

## Methodology

1. Select a set of 200 documents, which have less than 10,000 tokens
2. Ask Claude Sonnet to generate a set of questions based on that single doc
3. Save the questions along with the reasoning

## Open Questions

1. Should multiple related documents be considered? Yes. Will evaluate this too