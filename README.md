A simple tool for scraping the Humble Bundle website for new bundles using Selenium for Firefox.

The tool captures bundle names and stores them in a Postgres database so that each bundle is only scraped once.

When a new bundle is found, information about the games and tiers are gathered and formatted into a markup message for Discord to ingest via a webhook.

<img width="605" height="742" alt="image" src="https://github.com/user-attachments/assets/b057e3be-b235-4dcc-92b0-f67f6096cfed" />
*An example of how a new bundle message displays in Discord*
