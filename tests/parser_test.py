"""Test rsokf.parser

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: https://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_chunks():
    from pykern import pkunit
    from rsokf import parser

    c = parser.chunks(pkunit.data_dir())
    pkunit.pkeq(4, len(c))

    # index.md and log.md are reserved: no frontmatter, sectioned by heading
    pkunit.pkeq("index.md", c[0].path)
    pkunit.pkeq("Tables", c[0].heading)
    pkunit.pkeq("* [Orders](tables/orders.md) - order records", c[0].text)
    pkunit.pkeq("log.md", c[1].path)
    pkunit.pkeq("2026-05-22", c[1].heading)
    pkunit.pkeq("* **Creation**: Added the orders table.", c[1].text)

    # concept documents: path drops .md (SPEC.md's "Concept ID"), each
    # section carries the frontmatter title/type/description as a prefix
    pkunit.pkeq("tables/orders", c[2].path)
    pkunit.pkeq("Schema", c[2].heading)
    pkunit.pkeq(
        "Title: Orders\nType: BigQuery Table\n"
        "Description: One row per completed customer order.\n\n"
        "Widget orders schema.",
        c[2].text,
    )
    pkunit.pkeq("tables/orders", c[3].path)
    pkunit.pkeq("Joins", c[3].heading)
    pkunit.pkre("^Title: Orders", c[3].text)
    pkunit.pkre("Joined with customers.$", c[3].text)

    for x in c:
        pkunit.pkok(isinstance(x.mtime, float), "mtime not a float chunk={}", x)
