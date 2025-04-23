# fit-cases

Case management module for the **FIT Project**, built using [PySide6](https://doc.qt.io/qtforpython/).

This module provides the graphical interface to modify case information used by the FIT application.

---

## 🔗 Related FIT components

This package is part of the broader [fit](https://github.com/fit-project/fit) ecosystem and depends on:

- [`fit-common`](https://github.com/fit-project/fit-common) – shared utility and core logic
- [`fit-assets`](https://github.com/fit-project/fit-assets) – UI resources and assets
- [`fit-configurations`](https://github.com/fit-project/fit-configurations.git) – Configuration settings

---

## 🐍 Dependencies

Main dependencies are:

- Python `>=3.9,<3.13`
- [`PySide6`](https://pypi.org/project/PySide6/) 6.9.0
- [`SQLAlchemy`](https://pypi.org/project/SQLAlchemy/) ^2.0.40
- `fit-common` (custom submodule)
- `fit-assets` (custom submodule)
- `fit-configurations` (custom submodule)

See `pyproject.toml` for full details.

---

## 🚀 Installation

Install the module using [Poetry](https://python-poetry.org/):

```bash
poetry install

