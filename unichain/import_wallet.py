import asyncio
from playwright.async_api import async_playwright

async def import_to_rabby(page, private_key):
    """Импорт приватного ключа в Rabby Wallet"""
    extension_url = "chrome-extension://acmacodkjbdgmoleebolmdjonilkdbch/index.html#"
    try:
        # Ждем загрузки страницы
        await page.wait_for_load_state("domcontentloaded")

        # Нажимаем на кнопку импорта приватного ключа
        import_button = page.locator("button:has-text('I already have an address')")
        await import_button.click()
        await asyncio.sleep(1)
        private_key_button = page.locator("div.rabby-ItemWrapper-rabby--mylnj7:has-text('Private Key')")
        await private_key_button.click()
        await asyncio.sleep(1)
        await page.fill("#privateKey", private_key.replace('0x', ''))
        # Вводим приватный ключ
        await asyncio.sleep(1)
        confirm_button = page.locator("button.ant-btn-primary:has-text('Confirm')")
        await confirm_button.click()
        await asyncio.sleep(1)

        await page.fill("#password", "password12345")
        await page.fill("#confirmPassword", "password12345")

        checked = page.locator("div.text-r-blue-default")
        has_checked = await checked.count() > 0

        if has_checked:
            confirm_button = page.locator("button.ant-btn-primary:has-text('Confirm')")
            await confirm_button.click()
        else:
            neutral_div = page.locator("div.text-r-neutral-foot")
            await neutral_div.click()
            await asyncio.sleep(1)

            confirm_button = page.locator("button.ant-btn-primary:has-text('Confirm')")
            await confirm_button.click()

        await asyncio.sleep(1)
        get_started_button = page.locator("button.ant-btn-primary:has-text('Get Started')")
        await get_started_button.click()
        await asyncio.sleep(1)
        await page.goto(extension_url)
        await page.wait_for_load_state("domcontentloaded")
        current_url = page.url
        if extension_url in current_url:
            close_modal = page.locator("span.ant-modal-close-x")
            await close_modal.click()
            return True

    except Exception as e:
        print(f"Ошибка при импорте кошелька в Rabby: {e}")
        return False