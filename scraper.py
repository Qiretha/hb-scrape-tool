import configparser
import re
import time
import discord
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import psycopg2
from discord import SyncWebhook

# To-do
# - figure out adding multiple webhooks
# - code clean up. There's too much going on in some of the functions
# - improve display of multi-tier bundles

driver = webdriver.Firefox()


def get_game_tiers():
    # game tiers
    games_collection = driver.find_elements(By.XPATH, "//span[@class='item-title']")

    tiers_games_dict = {}

    # If the bundle has multiple tiers
    if driver.find_elements(By.XPATH, "//div[@class='tier-filters']"):
        tier_options = driver.find_elements(By.XPATH, "//a[contains(@class, 'js-tier-filter')]")
        tier_price_size = {}

        games_dict = {}

        first = True
        for tier in reversed(tier_options):
            tier_size = re.search(r'\d+', tier.text).group()
            tier.click()
            if first:
                tier_price = driver.find_element(By.XPATH, "//h3[contains(@class, 'tier-header')]").text
                first = False
            else:
                tier_price = driver.find_element(By.XPATH, "//h3[contains(@class, 'tier-header')]").text + \
                             " (Includes previous tier)"

            # Go through each option from least to most games and add them to a dictionary
            # Had to use dictionary to preserve order.
            games_collection = driver.find_elements(By.XPATH, "//span[@class='item-title']")
            for game in games_collection:
                game_name = "- " + game.text
                games_dict[game_name] = None

            tier_price_size[tier_price] = int(tier_size)

        prev_size = 0
        for price_quote, size in tier_price_size.items():
            # Create dictionary item containing the tier, price + no. of games and the game names
            tiers_games_dict[price_quote] = list(games_dict)[prev_size:size]
            prev_size = size
    else:
        # If the bundle is a single tier
        single_tier_items = driver.find_element(By.XPATH, "//h3[contains(@class, 'tier-header')]").text

        games_list = []
        for game in games_collection:
            game_name = "- " + game.text
            games_list.append(game_name)

        tiers_games_dict[single_tier_items] = games_list

    return tiers_games_dict


def get_list_of_games(new_bundle):
    driver.get(new_bundle)
    WebDriverWait(driver, 20).until(EC.visibility_of_element_located(
        (By.XPATH, "//div[@class='desktop-tier-collection-view']")))

    tiers_games_dict = get_game_tiers()

    message = build_discord_message(tiers_games_dict)

    send_discord_message(new_bundle, message)


def build_discord_message(tiers_games_dict):
    message = ""
    for key, value in tiers_games_dict.items():
        message += '***' + key + '***\n' + '\n'.join([str(i) for i in value]) + '\n\n'

    return message


def send_discord_message(new_bundle, games_list):
    a_webhook = config['Webhooks']['temp_webhook_var']
    webhook = SyncWebhook.from_url(a_webhook)

    webhook.send(content=new_bundle,
                 avatar_url="https://cdn.humblebundle.com/static/hashed/03de04a2224923e1ff35c11a3a1cd0e675b5003e.png")

    embed = discord.Embed(title="Games in this bundle:", description=games_list, color=0xd0011b)
    webhook.send(embed=embed)


def search_humble():
    driver.get("https://www.humblebundle.com/games")
    # Give the page a chance to fully load before searching
    WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.XPATH, "//div[@class='info-section']")))
    bundles = driver.find_elements(By.XPATH, "//div[@class='info-section']")

    built_bundles = [["" for _ in range(2)] for _ in range(len(bundles))]
    pos = 0  # position of cursor in 'links' list
    for bundle in bundles:
        built_bundles[pos][0] = ("https://www.humblebundle.com" + bundle.get_attribute('href').split("?")[0])
        built_bundles[pos][1] = bundle.text.split("\n")[0]
        pos += 1

    for bundle in built_bundles:
        bundle_link = bundle[0]
        bundle_title = bundle[1]
        cur.execute("SELECT EXISTS(SELECT 1 FROM humbleBundles WHERE name = %s OR link = %s);",
                    (bundle_title, bundle_link))

        exists = cur.fetchone()[0]

        if not exists:
            print("New bundle " + bundle_title.lower() + " found!")

            get_list_of_games(bundle_link)

            # Save the new bundle in the database so that it is ignored next time.
            cur.execute("INSERT INTO humblebundles "
                        "VALUES (%s, %s);",
                        (bundle_title, bundle_link))
            conn.commit()
            time.sleep(1)
        else:
            # If bundle has been seen before, print message and continue to next bundle
            print(bundle_title + " already found, ignoring...")


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read('config.ini')

    db = config['Credentials']['database_name']
    user = config['Credentials']['database_username']
    password = config['Credentials']['database_pass']

    print('Connecting to the PostgreSQL database...')
    conn = psycopg2.connect(dbname=db, user=user, password=password)

    # Create a cursor - DB will execute a statement, then keep the result stored in DB memory
    cur = conn.cursor()

    print('PostgreSQL database version: ', end='')
    cur.execute('SELECT version()')

    db_version = cur.fetchone()
    print(db_version)

    search_humble()

    try:
        cur.close()
        print('Database connection closed')
    except Exception as err:
        print(f'Uh oh, an error occurred: {err}')
    finally:
        driver.quit()
        print('Finished :)')

