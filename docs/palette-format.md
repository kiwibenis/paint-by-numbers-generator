# Palette Format

Reference palettes are stored as JSON files.

This document defines the storage format completely: the shape of a document,
every field, every bound the loader enforces, the file name and the versioning
rules. A palette that satisfies everything here loads.

It does not say which values to choose. How to source, justify and document a
palette is a separate question, answered in
[`palette-authoring-guide.md`](palette-authoring-guide.md). That document
points here for every mechanical rule rather than restating one, because two
places stating the same rule is how the two stop agreeing.

## Document Shape

A palette document has exactly two top-level fields:

```json
{
    "metadata": {},
    "colors": []
}
```

`metadata` holds exactly `id`, `manufacturer`, `display_name` and `version`.

Each entry in `colors` holds exactly `number`, `name` and `rgb`, and each
`rgb` holds exactly `red`, `green` and `blue`.

A missing field and an unknown field are both rejected. Unknown fields are not
ignored: a document decides what a palette contains, and a document the loader
only partly understands is one it has no business accepting.

## Metadata

| Field         | Type    | Description                                       |
| ------------- | ------- | ------------------------------------------------- |
| id            | string  | Unique palette identifier.                        |
| manufacturer  | string  | Palette manufacturer.                             |
| display_name  | string  | Human-readable palette name.                      |
| version       | integer | Palette version. Released versions are immutable. |

## Colors

Each palette color contains the following fields:

| Field     | Type    | Description                         |
| --------- | ------- | ----------------------------------- |
| number    | integer | Official manufacturer color number. |
| name      | string  | Official manufacturer color name.   |
| rgb.red   | integer | Red component (0–255).              |
| rgb.green | integer | Green component (0–255).            |
| rgb.blue  | integer | Blue component (0–255).             |

The position of an entry in the array is not its number. Nothing derives a
number from it, and the quantizer builds its own index space rather than
using it. The order is still observable: the legend is printed in it, which
is why reordering a released palette is a modification like any other.

## Bounds

Every bound below is enforced when a palette is loaded.

| Bound | Value |
|---|---|
| Document size | 1,048,576 bytes |
| Colors per palette | 1 to 256 |
| Text field length | 1 to 128 characters |
| Renderable characters | 218 |
| Color number | integer, 1 or greater |
| RGB channel | integer, 0 to 255 |
| Identifier | 1 to 64 characters from `A-Z`, `a-z` and `0-9` |
| Version | 1 to 9999 |

`true` and `false` are not accepted where an integer is required, although
Python treats them as integers.

The 256-color limit is architectural rather than arbitrary. `QuantizedImage`
stores one palette index per pixel in one byte, per ADR-0017, so a larger
palette cannot be represented by the current quantized-image model. Changing
it requires an architectural decision.

`tests/test_palette_format_documentation.py` compares every value in that
table against the constant that enforces it, so this table cannot quietly
fall behind the loader.

## Text

`manufacturer`, `display_name` and every color `name` are rendered into the
PDF legend by the built-in fonts, which are WinAnsi.

A character outside that encoding is not refused by the PDF library; it is
replaced by an unrelated symbol, so a palette containing one would produce a
legend that no longer states which pencil a number means. The loader rejects
such a document instead, naming the offending code points as `U+XXXX`.

The renderable set is the 218 printable WinAnsi characters. It covers Latin
text and the common Latin accents, so all of the following are accepted:

```text
Grün
Bleu Céruleum
Niño
Åkerblom
```

The bound is the renderer's rather than a preference for Latin script. It is
asserted against the renderer in `tests/test_palette_text_is_renderable.py`,
so the two cannot drift apart.

## Uniqueness

`number` must be unique within a palette. It is the manufacturer's reference
and, at the same time, the label printed inside every region of that colour,
so a repeated number produces a template a painter cannot follow: the legend
offers two paints under the number the region shows. A document that repeats
one is rejected when it is loaded.

`name` and the `rgb` triple are not checked for uniqueness at this boundary.
Two entries with one RGB value are one colour to the quantizer, so the second
can never appear on a generated template while still being printed in the
legend; `tests/test_palette_rgb_uniqueness.py` holds the shipped palettes to
that, and `palette-authoring-guide.md` explains why it matters when authoring
one.

## Versioning

Reference palettes follow the project's palette versioning strategy
(ADR-0007).

The combination of `id` and `version` uniquely identifies a palette.

Released palette versions are immutable.

Each palette version is stored as a separate JSON file using the following
filename convention:

<palette-id>-v<version>.json

For example:

palettes/
├── faberCastellPolychromos60-v1.json
├── faberCastellPolychromos60-v2.json
└── reference8-v1.json

The identifier and the version are bounded, because the identifier reaches a
file system path and the pair has to survive being written into a file name
and read back out of one. The two bounds are in the table above.

A file the generator will not offer is one it also cannot load, and the
reverse: `pbn.infrastructure.palette_file_name` decides both, so
`pbn palettes` never lists a palette that `--palette` then rejects. A name
outside these bounds is skipped by the catalogue rather than reported, so a
palette that does not appear in `pbn palettes` should be checked against that
table first.

The palette identifier and version in the filename must match the corresponding
values in the JSON metadata.

For example, `faberCastellPolychromos60-v1.json` must contain:

{
    "metadata": {
        "id": "faberCastellPolychromos60",
        "version": 1
    }
}

Any modification to a released palette, including:

- metadata;
- color numbers;
- color names;
- RGB reference values;
- the order of the entries;

requires a new palette version and therefore a new palette file.

Released palette files must never be modified.

## Example

{
    "metadata": {
        "id": "faberCastellPolychromos60",
        "manufacturer": "Faber-Castell",
        "display_name": "Polychromos 60",
        "version": 1
    },
    "colors": [
        {
            "number": 101,
            "name": "White",
            "rgb": {
                "red": 255,
                "green": 255,
                "blue": 255
            }
        }
    ]
}

## What this document does not decide

A document can satisfy every rule here and still be the wrong palette to
ship. Which number, name and RGB value an entry should carry, what evidence
supports them, how a correction is handled and what has to be recorded in
`docs/reference-data/` are decisions, and
[`palette-authoring-guide.md`](palette-authoring-guide.md) is authoritative
for them.
