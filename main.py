import asyncio
from rich.console import Console
from rich.prompt import Prompt
from prompt_toolkit import prompt
from rng_lib import RNG
import nest_asyncio

console = Console()

network_data = {
    0: {
        "name": "Preprod",
        "blockfrostURL": "https://cardano-preprod.blockfrost.io/api/v0",
    },
    1: {
        "name": "Mainnet",
        "blockfrostURL": "https://cardano-mainnet.blockfrost.io/api/v0",
    },
}


async def get_base_params():
    network = int(
        prompt("Which network ? \n Type 1 for Mainnet \n Type 0 for Preprod: "))
    blockfrost_api_key = prompt("Enter Blockfrost api key: ")
    rng_api_url = prompt("Enter the hosted RNG API URL: ")
    ogmios_url = prompt("Enter the hosted Ogmios URL: ")
    oracle_cbor = prompt("Enter Oracle Contract compiled CBOR: ")
    rng_cbor = prompt("Enter RNG Contract compiled CBOR: ")
    wallet_seed = prompt(
        "Enter 12, 15 or 24 words wallet seed (should have atleast 5-10 ADA) to perform actions: ")
    rng_output_len = int(prompt("Enter your desired Random Number length: "))

    return {
        "network": network,
        "blockfrost_api_key": blockfrost_api_key,
        "rng_api_url": rng_api_url,
        "ogmios_url": ogmios_url,
        "oracle_cbor": oracle_cbor,
        "rng_cbor": rng_cbor,
        "wallet_seed": wallet_seed,
        "rng_output_len": rng_output_len,
    }

def sleep(ms):
    return asyncio.sleep(ms / 1000)


nest_asyncio.apply()


async def main():
    base_params = await get_base_params()
    instance = RNG(blockfrostApiKey=base_params["blockfrost_api_key"],
                   network=base_params["network"],
                   ogmiosUrl=base_params["ogmios_url"],
                   oracleCBOR=base_params["oracle_cbor"],
                   rngAPIURL=base_params["rng_api_url"],
                   rngCBOR=base_params["rng_cbor"],
                   rngOutputLen=base_params["rng_output_len"],
                   walletSeed=base_params["wallet_seed"])

    base_oracle_did = None
    curr_oracle_updated_tx = None

    while True:
        if not base_oracle_did:
            console.print("[green]Creating Oracle DID for you")
            oracle_did_name = prompt(
                "Enter your desired name for Oracle DID: ")
            console.print("Minting Oracle DID to your wallet...", end="")

            data = instance.mint(oracle_did_name)

            if not data['data'].get('txHash'):
                console.print(f"[red]\nFailed: {data.get('error')}")
                break

            console.print("[green]Minting successful")
            console.print(
                f"Waiting for transaction: {data['data']['txHash'][:6]}... to be confirmed")

            await sleep(120 * 1000)
            base_oracle_did = {
                "unit": data['data']["oracleDIDUnit"], "registered": False}

        if base_oracle_did and not base_oracle_did["registered"]:
            console.print(
                "[green]To register the Oracle DID, We need initial RNG Transaction to pass the data with it")
            initRNGData = instance.init()
            console.print("Initiating RNG ID to RNG Contract...")

            print(data)

            if not initRNGData['data']:
                break

            await sleep(120 * 1000)
            
            console.print("Registering Oracle DID to Oracle Contract...")
            register_data = instance.register(
                initRNGTx=initRNGData['data']['txHash'], oracleDIDUnit=base_oracle_did['unit'])

            if not register_data['data'].get('txHash'):
                break

            await sleep(120 * 1000)
            curr_oracle_updated_tx = register_data['data']["txHash"]
            base_oracle_did["registered"] = True

        action_type = int(prompt(
            "Following actions you can do with\n1. Generate new RNG\n2. Query Oracle DID: "))

        if action_type == 1 and curr_oracle_updated_tx:
            rng_output_len = int(
                prompt("Enter your desired Random Number length: "))
            instance.rngOutputLen = rng_output_len

            console.print("Initiating RNG ID to RNG Contract...")
            data = instance.init()
            if not data['data']:
                break

            await sleep(120 * 1000)
            console.print("Updating Oracle DID to Oracle Contract...")
            update_data = instance.update(
                initRNGTx=data['data']['txHash'], oracleDIDUnit=base_oracle_did['unit'], currUpdatedOracleDIDTx=curr_oracle_updated_tx)

            if not update_data['data'].get('txHash'):
                break

            await sleep(120 * 1000)
            curr_oracle_updated_tx = update_data['data']['txHash']

        if action_type == 2 and curr_oracle_updated_tx:
            data = instance.query(curr_oracle_updated_tx)
            console.print(
                f"[green]Random Number from Oracle: {data['data']['rngOutput']}")

asyncio.run(main())
