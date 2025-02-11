import os
import asyncio
import sys
from colorama import init, Fore, Style
from web3 import Web3
from eth_account import Account
from playwright.async_api import async_playwright
from fake_useragent import UserAgent
from dotenv import load_dotenv
import random
from decimal import Decimal

load_dotenv()
init()

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

class WalletStatus:
    def __init__(self, address):
        self.address = address
        self.action = ""
        self.status = "NEED CHECK"

    def update_status(self, status):
        self.status = status

    def update_action(self, action):
        self.action = action

    def get_colored_status(self):
        if self.status == "NEED CHECK":
            return f"{Fore.WHITE}{self.status}{Style.RESET_ALL}"
        elif self.status == "PROCESS":
            return f"{Fore.YELLOW}{self.status}{Style.RESET_ALL}"  # Изменили на оранжевый (желтый)
        elif self.status == "SUCCESS":
            return f"{Fore.GREEN}{self.status}{Style.RESET_ALL}"
        else:  # ERROR
            return f"{Fore.RED}{self.status}{Style.RESET_ALL}"

    def display(self, index):
        return f"{index}. {self.address} | {self.action} | {self.get_colored_status()}"

def check_nft_balances(address):
    """Проверяет балансы обоих NFT"""
    try:
        w3 = Web3(Web3.HTTPProvider("https://unichain-sepolia-rpc.publicnode.com"))

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
                    '--disable-blink-features=AutomationControlled',
                    '--headless=new',
                ],
                user_agent=user_agent,
            )

            await asyncio.sleep(5)

            titles = [await p.title() for p in context.pages]
            while 'Rabby Wallet' not in titles:
                titles = [await p.title() for p in context.pages]
            rabby_page = context.pages[1]

            # TODO: Здесь будет код для минта NFT
            success = await import_to_rabby(rabby_page, private_key)
            if not success:
                print("Ошибка при импорте кошелька")
                await context.close()
                return

            # TODO: Здесь будет код для минта NFT
            address = Account.from_key(private_key).address
            has_unicorn, has_morkie = check_nft_balances(address)

            if not has_unicorn or not has_morkie:

                if not has_unicorn:
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

            await context.close()
            return True

    except Exception as e:
        print(f"Ошибка при работе с браузером: {e}")

async def process_wallet_with_status(private_key, wallet_path, status_dict):
    """Обработка одного кошелька с обновлением статуса"""
    try:
        address = Account.from_key(private_key).address
        wallet_status = status_dict[address]

        try:
            if not private_key.startswith('0x'):
                private_key = '0x' + private_key

            # Проверяем наличие NFT
            has_unicorn, has_morkie = check_nft_balances(address)

            if wallet_status.action == "CHECK AND MINT NFT'S":
                if not has_unicorn or not has_morkie:
                    wallet_status.update_status("PROCESS")  # Меняем статус на PROCESS перед началом минта
                    mint_success = await handle_browser_actions(wallet_path, private_key)
                    wallet_status.update_status("SUCCESS" if mint_success else "ERROR")
                else:
                    wallet_status.update_status("SUCCESS")
                    print("NFT уже есть на балансе")

            elif wallet_status.action == "BRIDGE":
                wallet_status.update_status("PROCESS")  # Меняем статус на PROCESS перед началом бриджа
                await display_interface(status_dict)  # Добавляем обновление интерфейса

                bridge = UnichainBridge(private_key)
                initial_eth = bridge.check_eth_balance()

                if initial_eth < Decimal('0.001'):
                    wallet_status.update_status("ERROR")
                    await display_interface(status_dict)  # Обновляем интерфейс
                    return

                success = await bridge.bridge_eth_to_weth(float(initial_eth) * 0.5)
                if success:
                    success = await bridge.weth_to_eth(float(initial_eth) * 0.5)

                wallet_status.update_status("SUCCESS" if success else "ERROR")
                await display_interface(status_dict)  # Обновляем интерфейс

            elif wallet_status.action == "MINT NFT'S AND BRIDGE":
                if not has_unicorn or not has_morkie:
                    wallet_status.update_status("PROCESS")  # Меняем статус на PROCESS перед началом минта
                    await display_interface(status_dict)  # Добавляем обновление интерфейса

                    mint_success = await handle_browser_actions(wallet_path, private_key)
                    if not mint_success:
                        wallet_status.update_status("ERROR")
                        await display_interface(status_dict)  # Обновляем интерфейс
                        return

                wallet_status.update_status("PROCESS")  # Обновляем статус перед началом бриджа
                await display_interface(status_dict)  # Добавляем обновление интерфейса

                bridge = UnichainBridge(private_key)
                initial_eth = bridge.check_eth_balance()

                if initial_eth < Decimal('0.001'):
                    wallet_status.update_status("ERROR")
                    await display_interface(status_dict)  # Обновляем интерфейс
                    return

                success = await bridge.bridge_eth_to_weth(float(initial_eth) * 0.5)
                if success:
                    success = await bridge.weth_to_eth(float(initial_eth) * 0.5)

                wallet_status.update_status("SUCCESS" if success else "ERROR")
                await display_interface(status_dict)  # Обновляем интерфейс

        except Exception as e:
            print(f"Ошибка при обработке кошелька {address}: {e}")
            wallet_status.update_status("ERROR")
            await display_interface(status_dict)  # Обновляем интерфейс при ошибке

    except Exception as e:
        print(f"Критическая ошибка: {e}")
        await display_interface(status_dict)

async def display_interface(status_dict):
    """Отображение интерфейса"""
    os.system('cls' if os.name == 'nt' else 'clear')
    print("\nUNICHAIN MINT AND BRIDGE TESTNET\n")
    print("*" * 100)

    for i, (address, status) in enumerate(status_dict.items(), 1):
        print(status.display(i))

    print("*" * 100)

async def main():
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print("\nUNICHAIN MINT AND BRIDGE TESTNET\n")
        print("PICK VARIANT:")
        print("1. CHECK AND MINT NFT'S")
        print("2. BRIDGE")
        print("3. MINT NFT'S AND BRIDGE")
        print("4. EXIT")

        choice = input("\nВыберите действие (1-4): ")

        if choice == "4":
            sys.exit()

        if choice not in ["1", "2", "3"]:
            print("Неверный выбор. Попробуйте снова.")
            continue

        actions = {
            "1": "CHECK AND MINT NFT'S",
            "2": "BRIDGE",
            "3": "MINT NFT'S AND BRIDGE"
        }

        # Загрузка кошельков
        wallets_file = os.path.join(os.path.dirname(__file__), "wallets_input.txt")
        if not os.path.exists(wallets_file):
            print(f"Ошибка: Файл {wallets_file} не найден")
            return

        with open(wallets_file, "r") as file:
            private_keys = [line.strip() for line in file if line.strip()]

        # Создаем словарь статусов
        status_dict = {}
        for private_key in private_keys:
            address = Account.from_key(private_key).address
            status = WalletStatus(address)
            status.update_action(actions[choice])
            status_dict[address] = status

        wallet_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__),
            "0.93.12_0"
        ))

        # Создаем и запускаем задачи
        tasks = []
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_WALLETS)

        async def process_with_semaphore(private_key):
            async with semaphore:
                await process_wallet_with_status(private_key, wallet_path, status_dict)
                await display_interface(status_dict)

        for private_key in private_keys:
            task = asyncio.create_task(process_with_semaphore(private_key))
            tasks.append(task)

        # Запускаем задачу отображения интерфейса
        await display_interface(status_dict)

        # Ждем выполнения всех задач
        await asyncio.gather(*tasks)

        input("\nНажмите Enter для возврата в главное меню...")

if __name__ == "__main__":
    asyncio.run(main())