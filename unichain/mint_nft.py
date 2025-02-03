from playwright.async_api import Page
import asyncio
import time
async def handle_social_link(nft_page, link_url, context):
    try:
        # Сохраняем количество страниц до клика
        pages_before = len(context.pages)


        # Находим и кликаем по ссылке, используя частичное совпадение
        if "tweet?url" in link_url:
            link_element = nft_page.locator("a[href*='tweet?url']")
        elif "follow" in link_url:
            link_element = nft_page.locator("a[href*='follow']")
        elif "like" in link_url:
            link_element = nft_page.locator("a[href*='like']")
        else:
            link_element = nft_page.locator(f"a[href='{link_url}']")

        # Проверяем видимость элемента перед кликом
        await link_element.wait_for(state="visible", timeout=5000)
        await link_element.click()
        await asyncio.sleep(2)

        # Проверяем новые страницы
        pages_after = context.pages

        # Если появились новые страницы
        if len(pages_after) > pages_before:
            # Находим новую страницу
            for page in pages_after:
                if page != nft_page and ('twitter.com' in page.url or 'x.com' in page.url):
                    await page.close()
                    break

        return True

    except Exception as e:
        print(f"Ошибка при обработке ссылки {link_url}: {e}")

        return False

async def mint_nft_browser(rabby_page, nft_page, context):
    try:
        await nft_page.wait_for_load_state("domcontentloaded")

        # Список социальных ссылок
        social_links = [
            "https://twitter.com/intent/follow?screen_name=_morkie",
            "https://twitter.com/intent/like?tweet_id=1859954148986478724",
            "https://twitter.com/intent/tweet?url=https%3A%2F%2Fx.com%2F_morkie%2Fstatus%2F1859954148986478724"
        ]

        # Обрабатываем каждую ссылку
        for link in social_links:
            await handle_social_link(nft_page, link, context)
            await asyncio.sleep(1)

        link_element_id = nft_page.locator("h3:has-text('Mint Morkie ID')")
        await link_element_id.click()

        await asyncio.sleep(5)
        connect_button = nft_page.get_by_role("button", name="Connect")
        if await connect_button.count() > 0:
            await connect_button.click()
            await asyncio.sleep(1)
            rabby_button = nft_page.get_by_role("button", name="Rabby Wallet")
            await rabby_button.click()

            # Connect to Rabby Wallet
            rabby_window = None
            for i in range(10):
                for p in context.pages:
                    try:
                        title = await p.title()
                        if title == "Rabby Wallet Notification":
                            rabby_window = p
                            break
                    except:
                        continue
                if rabby_window:
                    break
                await asyncio.sleep(1)

            if rabby_window:

                try:
                    # Ждем загрузки страницы
                    await rabby_window.wait_for_load_state("domcontentloaded")
                    # Выводим все кнопки на странице
                    await asyncio.sleep(1)
                    connect_wallet_button = rabby_window.locator("button.ant-btn.ant-btn-primary.ant-btn-lg:has(span:text('Connect'))")
                    await connect_wallet_button.click()
                    await asyncio.sleep(1)

                except Exception as e:
                    print(f"Ошибка при работе с окном Rabby: {e}")
                    return False

            else:
                print("Окно Rabby Wallet Notification не найдено")
                return False
        else:
            print("Кнопка Connect не найдена")

        mint_button = nft_page.locator("button.primary-btn:has(span:text('Mint NFT'))")
        await mint_button.is_visible()
        await mint_button.click()
        await asyncio.sleep(2)
        #ADD TO WALLET
        rabby_window = None
        for i in range(10):
            for p in context.pages:
                try:
                    title = await p.title()
                    if title == "Rabby Wallet Notification":
                        rabby_window = p
                        break
                except:
                    continue
            if rabby_window:
                break
            await asyncio.sleep(1)
        if rabby_window:

            try:
                await rabby_window.wait_for_load_state("domcontentloaded")
                add_button = rabby_window.locator("button.ant-btn.ant-btn-primary.ant-btn-lg:has(span:text('Add'))")
                await asyncio.sleep(1)
                if await add_button.count() > 0:
                    await add_button.click()
                else:
                    print("Кнопка Add не найдена")
                await asyncio.sleep(1)

            except Exception as e:
                print(f"Ошибка при работе с окном Rabby: {e}")
                return False

        else:
            print("Окно Rabby Wallet Notification не найдено")
            return False
        # CONFIRM TXN
        rabby_window = None
        for i in range(10):
            for p in context.pages:
                try:
                    title = await p.title()
                    if title == "Rabby Wallet Notification":
                        rabby_window = p
                        break
                except:
                    continue
            if rabby_window:
                break
            await asyncio.sleep(1)
        if rabby_window:

            try:
                await rabby_window.wait_for_load_state("domcontentloaded")
                sign_button = rabby_window.locator("button.ant-btn.ant-btn-primary.rabby-ButtonStyled-rabby--izrepg:has(span:text('Sign'))")
                await sign_button.click()
                # await asyncio.sleep(1000)
                confirm_txn_button = rabby_window.get_by_role("button", name="Confirm")
                await confirm_txn_button.click()
                await asyncio.sleep(1)
                print("NFT unicorn minted")
                return True


            except Exception as e:
                print(f"Ошибка при работе с окном Rabby: {e}")
                return False

        else:
            print("Окно Rabby Wallet Notification не найдено")
            return False


    except Exception as e:
        print(f"Ошибка при минте NFT через браузер: {e}")
        return False

async def mint_nerzo_nft_browser(rabby_page, nerzo_nft_page, context):
    try:
        await nerzo_nft_page.wait_for_load_state("domcontentloaded")

        # Клик по кнопке Follow
        follow_button = nerzo_nft_page.locator("button svg[viewBox='0 0 512 512']").first
        await follow_button.click()
        await asyncio.sleep(2)

        # Закрываем новую вкладку Twitter если она открылась
        pages_after = context.pages
        for page in pages_after:
            if page != nerzo_nft_page and ('twitter.com' in page.url or 'x.com' in page.url):
                await page.close()
                break

        # Клик по кнопке Claim Pass
        claim_button = nerzo_nft_page.locator("button svg[viewBox='0 0 512 512']").nth(1)
        await claim_button.click()
        await asyncio.sleep(2)

        # Клик по кнопке Retweet
        retweet_button = nerzo_nft_page.locator("button svg[viewBox='0 0 640 512']")
        await retweet_button.click()
        await asyncio.sleep(2)

        # Закрываем новую вкладку Twitter если она открылась
        pages_after = context.pages
        for page in pages_after:
            if page != nerzo_nft_page and ('twitter.com' in page.url or 'x.com' in page.url):
                await page.close()
                break
        await asyncio.sleep(3)
        # Ждем появления кнопки Connect Wallet
        connect_button = nerzo_nft_page.locator("button[data-test='connect-wallet-button']")
        await connect_button.wait_for(state="attached", timeout=30000)
        await asyncio.sleep(3)
        await connect_button.click()

        # Выбираем Rabby Wallet
        rabby_button = nerzo_nft_page.get_by_role("button", name="Rabby Wallet")
        await rabby_button.click()

        # Connect to Rabby Wallet
        rabby_window = None
        for i in range(10):
            for p in context.pages:
                try:
                    title = await p.title()
                    if title == "Rabby Wallet Notification":
                        rabby_window = p
                        break
                except:
                    continue
            if rabby_window:
                break
            await asyncio.sleep(1)

        if rabby_window:

            try:
                await rabby_window.wait_for_load_state("domcontentloaded")
                connect_wallet_button = rabby_window.locator("button.ant-btn.ant-btn-primary.ant-btn-lg:has(span:text('Connect'))")
                await connect_wallet_button.click()
                await asyncio.sleep(1)

            except Exception as e:
                print(f"Ошибка при работе с окном Rabby: {e}")
                return False

        else:
            print("Окно Rabby Wallet Notification не найдено")
            return False

        # Ждем кнопку минта
        mint_button = nerzo_nft_page.locator("button:has-text('Mint NFT')")
        await mint_button.wait_for(state="visible", timeout=5000)
        await mint_button.click()

        # Обработка подтверждения в Rabby
        rabby_window = None
        for i in range(10):
            for p in context.pages:
                try:
                    title = await p.title()
                    if title == "Rabby Wallet Notification":
                        rabby_window = p
                        break
                except:
                    continue
            if rabby_window:
                break
            await asyncio.sleep(1)

        if rabby_window:
            try:
                await rabby_window.wait_for_load_state("domcontentloaded")
                confirm_button = rabby_window.locator("button.ant-btn.ant-btn-primary.ant-btn-lg:has(span:text('Confirm'))")
                await confirm_button.click()
                await asyncio.sleep(1)
                print("Nerzo NFT minted successfully")
                return True

            except Exception as e:
                print(f"Ошибка при подтверждении транзакции: {e}")
                return False

        else:
            print("Окно подтверждения Rabby не найдено")
            return False

    except Exception as e:
        print(f"Ошибка при минте Nerzo NFT: {e}")
        return False
