from web3 import Web3
from eth_account import Account
from eth_abi import encode
import time

# ABI для WETH контракта
WETH_ABI = [
    {
        "constant": False,
        "inputs": [],
        "name": "deposit",
        "outputs": [],
        "payable": True,
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [{"name": "owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": False,
        "inputs": [{"name": "wad", "type": "uint256"}],
        "name": "withdraw",
        "outputs": [],
        "payable": False,
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

# Адреса контрактов в Unichain Sepolia
WETH_ADDRESS = "0x4200000000000000000000000000000000000006"  # Адрес WETH в Unichain Sepolia

class UnichainBridge:
    def __init__(self, private_key):
        # Проверяем подключение к сети
        self.w3 = Web3(Web3.HTTPProvider("https://unichain-sepolia.infura.io/v3/656c3f5d53c6415eac13761f9e552739"))
        if not self.w3.is_connected():
            raise Exception("Failed to connect to Unichain network")

        # Проверяем chain_id
        chain_id = self.w3.eth.chain_id

        self.account = Account.from_key(private_key)

        # Проверяем контракт WETH
        weth_address = Web3.to_checksum_address(WETH_ADDRESS)

        try:
            # Пробуем получить код контракта
            contract_code = self.w3.eth.get_code(weth_address)
            if contract_code == b'':
                raise Exception("No contract code found at the specified address")
        except Exception as e:
            print(f"Error checking WETH contract: {e}")
            raise

        self.weth_contract = self.w3.eth.contract(
            address=weth_address,
            abi=WETH_ABI
        )

    def check_eth_balance(self):
        balance = self.w3.eth.get_balance(self.account.address)
        return self.w3.from_wei(balance, 'ether')

    def check_weth_balance(self):
        balance = self.weth_contract.functions.balanceOf(self.account.address).call()
        return self.w3.from_wei(balance, 'ether')

    async def bridge_eth_to_weth(self, amount_in_eth):
        try:
            amount_in_wei = self.w3.to_wei(amount_in_eth, 'ether')

            # Проверяем nonce
            nonce = self.w3.eth.get_transaction_count(self.account.address)

            # Проверяем gas price
            gas_price = self.w3.eth.gas_price

            try:
                # Пробуем оценить газ
                gas_estimate = self.weth_contract.functions.deposit().estimate_gas({
                    'from': self.account.address,
                    'value': amount_in_wei
                })
            except Exception as e:
                print(f"Error estimating gas: {e}")
                return False

            # Создаем транзакцию с явным указанием chainId
            transaction = self.weth_contract.functions.deposit().build_transaction({
                'from': self.account.address,
                'value': amount_in_wei,
                'gas': gas_estimate,
                'gasPrice': gas_price,
                'nonce': nonce,
                'chainId': self.w3.eth.chain_id
            })


            # Подписываем транзакцию
            signed_txn = self.w3.eth.account.sign_transaction(transaction, self.account.key)

            # Отправляем транзакцию
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)

            # Ждем подтверждения транзакции
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

            if receipt['status'] == 1:
                return True
            else:
                print("Transaction failed!")
                return False

        except Exception as e:
            print(f"Error during bridge: {str(e)}")
            return False

    async def weth_to_eth(self, amount_in_eth):
        try:
            amount_in_wei = self.w3.to_wei(amount_in_eth, 'ether')

            # Проверяем nonce
            nonce = self.w3.eth.get_transaction_count(self.account.address)

            # Проверяем gas price
            gas_price = self.w3.eth.gas_price

            try:
                # Пробуем оценить газ
                gas_estimate = self.weth_contract.functions.withdraw(amount_in_wei).estimate_gas({
                    'from': self.account.address
                })
            except Exception as e:
                print(f"Error estimating gas: {e}")
                return False

            # Создаем транзакцию
            transaction = self.weth_contract.functions.withdraw(amount_in_wei).build_transaction({
                'from': self.account.address,
                'gas': gas_estimate,
                'gasPrice': gas_price,
                'nonce': nonce,
                'chainId': self.w3.eth.chain_id
            })

            # Подписываем транзакцию
            signed_txn = self.w3.eth.account.sign_transaction(transaction, self.account.key)

            # Отправляем транзакцию
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)

            # Ждем подтверждения транзакции
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

            if receipt['status'] == 1:
                return True
            else:
                print("Transaction failed!")
                return False

        except Exception as e:
            print(f"Error during unwrap: {str(e)}")
            return False
