---
name: tui-frameworks
description: Terminal UI framework standards — Python Textual, Rust Ratatui, Go Bubbletea, JS Ink, patterns, and accessibility
---

# TUI Frameworks

## Python — Textual (0.50+)

```python
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DataTable, Input
from textual.screen import ModalScreen

class DashboardApp(App):
    CSS_PATH = "dashboard.tcss"
    BINDINGS = [("q", "quit", "Quit"), ("d", "toggle_dark", "Dark Mode")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable(id="portfolio-table")
        yield Input(placeholder="Search...")
        yield Footer()

    async def on_mount(self) -> None:
        table = self.query_one("#portfolio-table", DataTable)
        table.add_columns("Ticker", "Price", "Change")
        data = await self.fetch_portfolio_data()
        for row in data:
            table.add_row(*row)
```

## Rust — Ratatui (0.26+)

```rust
use ratatui::{
    backend::CrosstermBackend,
    widgets::{Block, Borders, Table, Row, Cell},
    Terminal,
};

fn draw(f: &mut Frame, app: &App) {
    let rows: Vec<Row> = app.items.iter().map(|item| {
        Row::new(vec![
            Cell::from(item.ticker.as_str()),
            Cell::from(format!("{:.2}", item.price)),
        ])
    }).collect();

    let table = Table::new(rows, &[Constraint::Percentage(50), Constraint::Percentage(50)])
        .header(Row::new(vec!["Ticker", "Price"]).bold())
        .block(Block::default().borders(Borders::ALL).title("Portfolio"));

    f.render_widget(table, f.area());
}
```

## Key Patterns

1. **MVC/MVU**: Separate state model from rendering.
2. **Event-driven**: Handle keys, mouse, resize, custom events.
3. **Async data**: Load data in background, update on signal.
4. **Graceful cleanup**: Restore terminal on exit/panic.
5. **Color theming**: Support both light and dark terminals.
6. **Responsive layout**: Use constraint-based layouts.
