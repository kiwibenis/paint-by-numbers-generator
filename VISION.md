# Paint by Numbers Generator - Vision

## Vision

Create a professional, open-source Paint by Numbers generator that converts
photographs into high-quality printable templates.

The project aims to provide deterministic, reproducible and high-quality
results while maintaining a clean, testable and extensible architecture.

## Goals

The generator shall:

- produce professional paint-by-numbers templates;
- generate vector-based PDF output;
- support versioned reference palettes;
- provide consistent color numbering across all generated images;
- generate reusable palette legends;
- support multiple palette manufacturers;
- remain deterministic and reproducible;
- be suitable for both command-line and future graphical applications.

## Quality Objectives

The project is developed according to its accepted Architecture Decision
Records (ADRs).

Key quality objectives are:

- clean layered architecture;
- secure-by-default implementation;
- immutable domain models;
- high test coverage;
- deterministic output;
- maintainable and extensible codebase;
- cross-platform compatibility;
- clear, comprehensive and maintainable project documentation for continued
  development.

## Long-Term Direction

The project is developed as a reusable Python library.

Command-line tools, graphical user interfaces and other applications shall
use the same Core without duplicating business logic.

Future enhancements may include improved segmentation algorithms,
additional export formats, support for further reference palettes and
interactive user interfaces.