import pytest, json
from ape import Contract, project, networks
from ethpm_types import ContractType
from eth_utils import encode_hex, keccak, to_hex, to_bytes

############ CONFIG FIXTURES ############

# Adjust the string based on the `asset` your strategy will use
# You may need to add the token address to `tokens` fixture.
@pytest.fixture(scope="session")
def asset(tokens):
    yield Contract(tokens["weth"])


# Adjust the amount that should be used for testing based on `asset`.
@pytest.fixture(scope="session")
def amount(asset, user, whale):
    amount = 100 * 10 ** asset.decimals()

    asset.transfer(user, amount, sender=whale)
    yield amount


############ STANDARD FIXTURES ############


@pytest.fixture(scope="session")
def daddy(accounts):
    yield accounts["0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52"]


@pytest.fixture(scope="session")
def user(accounts):
    yield accounts[0]


@pytest.fixture(scope="session")
def rewards(accounts):
    yield accounts[1]


@pytest.fixture(scope="session")
def management(accounts):
    yield accounts[2]


@pytest.fixture(scope="session")
def keeper(accounts):
    yield accounts[3]


@pytest.fixture(scope="session")
def tokens():
    tokens = {
        "weth": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        "dai": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
        "usdc": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    }
    yield tokens


@pytest.fixture(scope="session")
def whale(accounts):
    # In order to get some funds for the token you are about to use,
    # The Balancer vault stays steady ballin on almost all tokens
    # NOTE: If `asset` is a balancer pool this may cause issues on amount checks.
    yield accounts["0xBA12222222228d8Ba445958a75a0704d566BF2C8"]


@pytest.fixture(scope="session")
def weth(tokens):
    yield Contract(tokens["weth"])


@pytest.fixture(scope="session")
def weth_amount(user, weth):
    weth_amount = 10 ** weth.decimals()
    user.transfer(weth, weth_amount)
    yield weth_amount


@pytest.fixture(scope="session")
def factory(strategy):
    yield Contract(strategy.FACTORY())


@pytest.fixture(scope="session")
def set_protocol_fee(factory):
    def set_protocol_fee(protocol_fee=0):
        owner = factory.governance()
        factory.set_protocol_fee_recipient(owner, sender=owner)
        factory.set_protocol_fee_bps(protocol_fee, sender=owner)

    yield set_protocol_fee


@pytest.fixture(scope="session")
def create_strategy(management, keeper, rewards):
    def create_strategy(asset, performanceFee=1_000):
        
        str_to_slot = lambda text: int(keccak(text=text).hex(), 16)
        slot = str_to_slot("yearn.base.strategy.storage") - 1
        # networks.provider.get_storage_at(address, slot)
        strategy = management.deploy(project.Strategy, asset, "yStrategy-Example")
        strategy_abi = json.loads(strategy.contract_type.json(include={'abi'}))
        tokenized_abi = json.loads(project.load_contracts()['TokenizedStrategy'].contract_type.json(include={'abi'}))
        merged_abi = {'abi': tokenized_abi['abi'] + strategy_abi['abi']}
        strategy = Contract(strategy.address, contract_type=ContractType.parse_raw(json.dumps(merged_abi)))
        
        print(f'🚀🚀🚀🚀🚀 {strategy.targetVault()}')
        print(f'🚀🚀🚀🚀🚀 {strategy.test()}')
        # strategy = project.Strategy.at(strategy.address)
        strategy = project.TokenizedStrategy.at(strategy.address)
        strategy.setKeeper(keeper, sender=management)
        strategy.setPerformanceFeeRecipient(rewards, sender=management)
        strategy.setPerformanceFee(performanceFee, sender=management)

        return strategy

    yield create_strategy


@pytest.fixture(scope="session")
def create_oracle(management):
    def create_oracle(_management=management):
        oracle = _management.deploy(project.StrategyAprOracle)

        return oracle

    yield create_oracle


@pytest.fixture(scope="session")
def strategy(asset, create_strategy):
    strategy = create_strategy(asset)

    yield strategy


@pytest.fixture(scope="session")
def oracle(create_oracle):
    oracle = create_oracle()

    yield oracle


############ HELPER FUNCTIONS ############


@pytest.fixture(scope="session")
def deposit(strategy, asset, user, amount):
    def deposit(_strategy=strategy, _asset=asset, assets=amount, account=user):
        _asset.approve(_strategy, assets, sender=account)
        _strategy.deposit(assets, account, sender=account)

    yield deposit


@pytest.fixture(scope="session")
def RELATIVE_APPROX():
    yield 1e-5

def merge_abis(dict1, dict2):
    for key, value in dict2.items():
        if key in dict1 and isinstance(dict1[key], dict) and isinstance(value, dict):
            merge_abis(dict1[key], value)
        else:
            dict1[key] = value
    return dict1