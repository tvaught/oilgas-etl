from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress

from oilgas.classifier import DocumentClassifier
from oilgas.config import settings
from oilgas.database import Database
from oilgas.debug import draw_layout
from oilgas.document import DocumentBlock
from oilgas.extractors.pdf import PDFExtractor
from oilgas.layout import Layout
from oilgas.parsers.header import HeaderExtractor
from oilgas.parsers.product import ProductExtractor
from oilgas.parsers.property import PropertyExtractor
from oilgas.parsers.revenue import RevenueParser
from oilgas.parsers.revenue_line import RevenueLineExtractor
from oilgas.repositories.revenue import RevenueRepository

console = Console()

app = typer.Typer(
    help="Oil & Gas ETL",
    no_args_is_help=True,
)


@app.callback()
def main():
    """Oil & Gas ETL tools."""
    pass


def property_blocks(
    document,
) -> list[DocumentBlock]:

    blocks = []

    for page in document.pages:
        layout = Layout(page)

        blocks.extend(PropertyExtractor(layout).extract())

    return blocks


@app.command("init")
def init_db():
    """Initialize the DuckDB database."""
    db = Database()
    db.initialize()
    db.close()
    typer.echo("Database initialized()")


@app.command("inspect")
def inspect(pdf: Path):

    document = PDFExtractor.load(pdf)

    typer.echo(f"Pages: {document.page_count}")

    typer.echo()

    typer.echo(document.pages[0].text[:1000])


@app.command()
def classify(pdf: Path):

    document = PDFExtractor.load(pdf)

    print(DocumentClassifier.classify(document))


@app.command()
def head(pdf: Path, lines: int = 40):
    """Print the first N lines of page 1."""

    document = PDFExtractor.load(pdf)

    for line in document.pages[0].text.splitlines()[:lines]:
        print(line)


@app.command()
def words(
    pdf: Path,
    page: int = 1,
):
    """
    Dump every word with coordinates.
    """

    document = PDFExtractor.load(pdf)

    p = document.pages[page - 1]

    for word in p.words:
        print(f"{word.y0:7.1f} {word.x0:7.1f}  {word.text}")


@app.command()
def rows(
    pdf: Path,
    page: int = 1,
):

    document = PDFExtractor.load(pdf)

    layout = Layout(document.pages[page - 1])

    for row in layout.rows:
        print(f"{row.y:7.1f} | {row.text}")


@app.command()
def right_of(
    pdf: Path,
    phrase: str,
):

    document = PDFExtractor.load(pdf)

    layout = Layout(document.pages[0])

    p = layout.find_phrase(phrase)

    if p:
        print("LABEL:", p.text)

    print()

    for word in layout.words_right_of(p):
        print(word.text)


@app.command()
def draw(
    pdf: Path,
    output: Path = Path("layout.pdf"),
):
    """
    Draw bounding boxes around every extracted word.
    """

    draw_layout(pdf, output)

    typer.echo(f"Wrote {output}")


@app.command()
def header(pdf: Path):

    document = PDFExtractor.load(pdf)

    layout = Layout(document.pages[0])

    extractor = HeaderExtractor()
    header = extractor.extract(layout)

    print(f"Owner Number : {header.owner_number}")
    print(f"Operator     : {header.operator}")
    print(f"Check Number : {header.check_number}")
    print(f"Check Date   : {header.check_date}")
    print(f"Check Amount : {header.check_amount}")


@app.command()
def properties(
    pdf: Path,
):

    document = PDFExtractor.load(pdf)

    blocks = property_blocks(document)

    typer.echo(f"\nFound {len(blocks)} property blocks\n")

    for i, block in enumerate(blocks, start=1):
        typer.echo("=" * 80)
        typer.echo(f"PROPERTY {i}")
        typer.echo("=" * 80)

        typer.echo(block.header.text)

        typer.echo(f"Rows: {block.start_row} - {block.end_row}")

        typer.echo()


@app.command()
def products(pdf: Path):

    document = PDFExtractor.load(pdf)

    layout = Layout(document.pages[0])

    property_blocks = PropertyExtractor(layout).extract()

    for property_block in property_blocks:
        print("=" * 80)
        print(property_block.header.text)
        print()

        product_blocks = ProductExtractor(
            property_block,
        ).extract()

        for product_block in product_blocks:
            print(f"  PRODUCT: {product_block.metadata['product']}")

            for row in product_block.rows:
                print(f"      {row.text}")

            print()


@app.command()
def lines(
    pdf: Path,
    debug: bool = typer.Option(
        False,
        "--debug",
        help="Show tokenization and column assignment.",
    ),
):

    document = PDFExtractor.load(pdf)

    layout = Layout(document.pages[0])

    property_blocks = PropertyExtractor(layout).extract()

    for property_block in property_blocks:
        print("=" * 80)
        print(property_block.header.text)
        print()

        product_blocks = ProductExtractor(
            property_block,
        ).extract()

        for product_block in product_blocks:
            print(f"PRODUCT: {product_block.metadata['product']}")
            print()

            parsed_rows = RevenueLineExtractor(
                product_block,
                debug=debug,
            ).extract()

            for parsed in parsed_rows:
                for key, field in parsed.fields.items():
                    print(f"{key:22} : {field.text:15} (x={field.x:.1f})")

                print("-" * 60)

            print()


@app.command()
def parse(
    pdf: Path,
) -> None:
    """
    Parse a revenue statement and emit the complete object graph as JSON.
    """

    document = PDFExtractor.load(pdf)

    statement = RevenueParser().parse(
        document=document,
        source_file=pdf.name,
    )

    print(
        statement.model_dump_json(
            indent=2,
        )
    )


@app.command()
def ingest(
    source: Path,
    database: Path | None = None,
) -> None:
    """
    Parse one or more revenue statements and persist them.
    """

    database_path = database or settings.database

    if not source.exists():
        raise typer.BadParameter(f"{source} does not exist.")

    if source.is_dir():
        files = sorted(source.glob("*.pdf"))
    else:
        files = [source]

    console.print(f"[bold cyan]Importing {len(files)} PDF(s)...[/bold cyan]")

    with Database(database_path) as db:
        repo = RevenueRepository(db.connection)

        with Progress() as progress:
            task = progress.add_task(
                "Importing revenue statements...",
                total=len(files),
            )

            for file in files:
                document = PDFExtractor.load(file)

                statement = RevenueParser().parse(document, source)

                repo.insert(file, statement)

                progress.console.print(f"✓ {file.name}")

                progress.advance(task)
