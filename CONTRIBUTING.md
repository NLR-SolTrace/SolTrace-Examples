# Contributing

Thanks for your interest in contributing to SolTrace-Examples.

## Contribution structure

Each contribution should be self-contained within its own directory. A contribution directory should include everything needed to understand and run the example, including a stand-alone `README.md`.

Example structure:

```text
example-name/
├── README.md
└── ...
```

## Required example README contents

Each contribution's `README.md` should answer the following questions:

1. **What does this demonstrate?**
2. **What do I need?**  
   List all requirements, dependencies, input data, and any environment setup.
3. **How do I run it?**  
   Provide step-by-step instructions that someone can follow from a clean checkout.
4. **What should I expect?**  
   Describe the expected outputs, behavior, or results so contributors and users can confirm the example worked.

## SolTrace version pinning

Contributions should pin to a specific version of SolTrace. Please document the exact SolTrace version your contribution was developed and tested against in the contribution `README.md`, and pin any related dependency or environment configuration accordingly.

Avoid instructions that rely on an unspecified "latest" version of SolTrace, since examples should remain reproducible over time.

## General guidance

- Keep contributions focused and reproducible.
- Include any required input files or clearly document how to obtain them.
- Prefer instructions that work without additional assumptions beyond the documented requirements.
