import os
import asyncio
from web3 import Web3
from eth_account import Account
from playwright.async_api import async_playwright
from fake_useragent import UserAgent
from dotenv import load_dotenv
import random

load_dotenv()

# Импортируем класс UnichainBridge из uniswap.py
from uniswap import UnichainBridge
from import_wallet import import_to_rabby
from mint_nft import mint_nft_browser

# Подключение к сети
infura_url = os.getenv("UNICHAIN_RPC_URL")
w3 = Web3(Web3.HTTPProvider(infura_url))

# NFT контракты
NFT_CONTRACT_ADDRESS_1 = os.getenv("UNICORN_NFT_ADDRESS") # Unicorn
NFT_CONTRACT_ADDRESS_2 = os.getenv('ALIEN_NFT_ADDRESS') # Alien
NFT_ABI = [
    {
        "inputs": [{"internalType": "address", "name": "owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]  # ABI NFT контракта
MAX_CONCURRENT_WALLETS = int(os.getenv('MAX_CONCURRENT_WALLETS', 3))
AMOUNT_TO_SWAP = float(os.getenv('AMOUNT_TO_SWAP', 0.001))

def check_nft_balances(address):
    """Проверяет балансы обоих NFT"""
    try:
        w3 = Web3(Web3.HTTPProvider("https://unichain-sepolia.infura.io/v3/656c3f5d53c6415eac13761f9e552739"))

        if not w3.is_connected():
            print("Ошибка подключения к сети Unichain")
            return False, False

        # Проверяем первый NFT (Unicorn)
        contract1 = w3.eth.contract(
            address=Web3.to_checksum_address(NFT_CONTRACT_ADDRESS_1),
            abi=NFT_ABI
        )
        balance1 = contract1.functions.balanceOf(
            Web3.to_checksum_address(address)
        ).call()

        # Проверяем второй NFT (Alien)
        contract2 = w3.eth.contract(
            address=Web3.to_checksum_address(NFT_CONTRACT_ADDRESS_2),
            abi=NFT_ABI
        )
        balance2 = contract2.functions.balanceOf(
            Web3.to_checksum_address(address)
        ).call()

        print(f"Баланс Unicorn NFT для адреса {address}: {balance1}")
        print(f"Баланс Alien NFT для адреса {address}: {balance2}")

        return balance1 > 0, balance2 > 0

    except Exception as e:
        print(f"Ошибка при проверке баланса NFT: {e}")
        return False, False

async def handle_browser_actions(wallet_path, private_key):
    """Функция для работы с браузером и Rabby wallet"""
    try:
        async with async_playwright() as p:
            user_agent = UserAgent().random
            context = await p.chromium.launch_persistent_context(
                "",
                channel="chromium",
                headless=True,
                args=[
                    '--disable-extensions-except=*',
                    f"--disable-extensions-except={wallet_path}",
                    '--disable-blink-features=AutomationControlled'
                ],
                user_agent=user_agent,
            )

            await asyncio.sleep(5)

            titles = [await p.title() for p in context.pages]
            while 'Rabby Wallet' not in titles:
                titles = [await p.title() for p in context.pages]
            rabby_page = context.pages[1]

            # TODO: Здесь будет код для минта NFT
            print("Браузер запущен")
            success = await import_to_rabby(rabby_page, private_key)
            if not success:
                print("Ошибка при импорте кошелька")
                await context.close()
                return

            # TODO: Здесь будет код для минта NFT
            print("Кошелек импортирован, готов к минту NFT")
            address = Account.from_key(private_key).address
            has_unicorn, has_morkie = check_nft_balances(address)

            if not has_unicorn or not has_morkie:
                print("Запуск минта отсутствующих NFT...")

                if not has_unicorn:
                    print("Минтим Unicorn NFT...")
                    unicorn_nft_page = await context.new_page()
                    await unicorn_nft_page.goto('https://morkie.xyz/unicorn')
                    for page in context.pages:
                        try:
                            title = await page.title()
                            if "Unicorn" in title:
                                unicorn_nft_page = page
                                break
                        except Exception as e:
                            print(f"Ошибка при проверке заголовка страницы: {e}")
                            continue
                    mint_success = await mint_nft_browser(rabby_page, unicorn_nft_page, context)
                    if not mint_success:
                        print("Ошибка при минте Unicorn NFT")
                        await context.close()
                        return False
                    await asyncio.sleep(2)

                if not has_morkie:
                    print("Минтим Alien NFT...")
                    alien_nft_page = await context.new_page()
                    await alien_nft_page.goto('https://morkie.xyz/alien')
                    for page in context.pages:
                        try:
                            title = await page.title()
                            if "UniChain Alien" in title:
                                alien_nft_page = page
                                break
                        except Exception as e:
                            print(f"Ошибка при проверке заголовка страницы: {e}")
                            continue
                    mint_success = await mint_nft_browser(rabby_page, alien_nft_page, context)
                    if not mint_success:
                        print("Ошибка при минте Alien NFT")
                        await context.close()
                        return False
            else:
                print("NFT уже есть на балансе, минт не требуется")

            print("Процесс успешно завершен")
            await context.close()
            return True

    except Exception as e:
        print(f"Ошибка при работе с браузером: {e}")

async def process_wallet(private_key, wallet_path):
    """Обработка одного кошелька"""
    try:
        if not private_key.startswith('0x'):
            private_key = '0x' + private_key

        w3 = Web3(Web3.HTTPProvider("https://unichain-sepolia.infura.io/v3/656c3f5d53c6415eac13761f9e552739"))
        address = Account.from_key(private_key).address
        print(f"\nОбработка кошелька: {address}")

        # Проверяем наличие NFT
        has_unicorn, has_morkie = check_nft_balances(address)

        if not has_unicorn or not has_morkie:
            print("Не все NFT найдены, запускаем браузер для минта...")
            mint_success = await handle_browser_actions(wallet_path, private_key)
            if mint_success:
                bridge = UnichainBridge(private_key)
        else:
            print("Оба NFT найдены, выполняем свап ETH-WETH-ETH...")
            bridge = UnichainBridge(private_key)

            # Проверяем баланс
        initial_eth = bridge.check_eth_balance()
        MIN_AMOUNT = 0.001
        initial_eth = bridge.check_eth_balance()

        if initial_eth < MIN_AMOUNT:
            print(f"Недостаточно ETH. Есть: {initial_eth}, Нужно минимум: {MIN_AMOUNT}")
            return
        max_amount = initial_eth - 0.0005  # Оставляем немного на газ
        AMOUNT = round(random.uniform(MIN_AMOUNT, max_amount), 6)  # Округляем до 6 знаков после запятой
            # ETH -> WETH
        success = await bridge.bridge_eth_to_weth(AMOUNT)
        if success:
            print("Успешно сконвертировали ETH в WETH")
            await asyncio.sleep(5)

            # WETH -> ETH
            success = await bridge.weth_to_eth(AMOUNT)
            if success:
                print("Успешно сконвертировали WETH обратно в ETH")
            else:
                print("Ошибка при конвертации WETH в ETH")
        else:
            print("Ошибка при конвертации ETH в WETH")

    except Exception as e:
        print(f"Ошибка при обработке кошелька: {e}")

async def process_wallets(private_keys, max_concurrent=MAX_CONCURRENT_WALLETS):
    """Обработка нескольких кошельков одновременно"""
    wallet_path = os.path.abspath(os.path.join(
        os.path.dirname(__file__),
        "0.93.12_0"
    ))

    # Создаем список задач
    tasks = []
    semaphore = asyncio.Semaphore(max_concurrent)

    async def process_with_semaphore(private_key):
        async with semaphore:
            return await process_wallet(private_key, wallet_path)

    # Создаем задачи для каждого кошелька
    for private_key in private_keys:
        task = asyncio.create_task(process_with_semaphore(private_key))
        tasks.append(task)

    # Ждем выполнения всех задач
    await asyncio.gather(*tasks)

async def main():
    wallets_file = os.path.join(os.path.dirname(__file__), "wallets_input.txt")

    if not os.path.exists(wallets_file):
        print(f"Ошибка: Файл {wallets_file} не найден")
        return

    with open(wallets_file, "r") as file:
        private_keys = [line.strip() for line in file if line.strip()]

    if not private_keys:
        print("Ошибка: Файл с приватными ключами пуст")
        return

    # Запускаем обработку всех кошельков параллельно
    print(f"Начинаем обработку {len(private_keys)} кошельков...")
    await process_wallets(private_keys, max_concurrent=3)
    print("Обработка всех кошельков завершена")

if __name__ == "__main__":
    asyncio.run(main())