---
name: web3-blockchain
description: Web3 and blockchain development — Hardhat, Foundry, OpenZeppelin, ethers.js, wagmi, DeFi patterns, ERC standards, and smart contract security
---

# Web3 & Blockchain Frameworks

## Development Frameworks

### Foundry (Preferred)
```toml
# foundry.toml
[profile.default]
src = "src"
out = "out"
libs = ["lib"]
optimizer = true
optimizer_runs = 200
solc_version = "0.8.20"

[profile.ci]
fuzz = { runs = 10000 }
invariant = { runs = 1000 }

[fmt]
line_length = 120
tab_width = 4
```

**Commands**: `forge build`, `forge test`, `forge coverage`, `forge snapshot` (gas), `forge script`.

### Hardhat
```typescript
// hardhat.config.ts
import { HardhatUserConfig } from "hardhat/config";
import "@nomicfoundation/hardhat-toolbox";
import "@openzeppelin/hardhat-upgrades";

const config: HardhatUserConfig = {
  solidity: {
    version: "0.8.20",
    settings: { optimizer: { enabled: true, runs: 200 } },
  },
  networks: {
    hardhat: { chainId: 1337 },
    sepolia: {
      url: process.env.SEPOLIA_RPC_URL!,
      accounts: [process.env.PRIVATE_KEY!],
    },
  },
  gasReporter: { enabled: true, currency: "USD" },
};
export default config;
```

---

## OpenZeppelin Contracts

| Contract | Import | Use |
|---|---|---|
| ERC20 | `@openzeppelin/contracts/token/ERC20/ERC20.sol` | Fungible tokens |
| ERC721 | `@openzeppelin/contracts/token/ERC721/ERC721.sol` | NFTs |
| ERC1155 | `@openzeppelin/contracts/token/ERC1155/ERC1155.sol` | Multi-token |
| Ownable | `@openzeppelin/contracts/access/Ownable.sol` | Simple access |
| AccessControl | `@openzeppelin/contracts/access/AccessControl.sol` | Role-based |
| ReentrancyGuard | `@openzeppelin/contracts/utils/ReentrancyGuard.sol` | Reentrancy |
| Pausable | `@openzeppelin/contracts/utils/Pausable.sol` | Emergency stop |
| UUPSUpgradeable | `@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol` | Upgrades |

**Rule: Always use OpenZeppelin for standard patterns. Never roll your own token or access control.**

---

## DeFi Patterns

### Staking
- Use ReentrancyGuard on all external calls.
- Track rewards per share (RewardPerToken pattern).
- Handle precision with 1e18 scaling.

### DEX/AMM
- Use constant product formula (x * y = k) or concentrated liquidity.
- Protect against sandwich attacks with deadline + slippage params.
- Flash loan fee on borrows.

### Governance
- Timelock controller for execution delay.
- Voting with ERC20Votes or ERC721Votes.
- Quorum requirements.

---

## Frontend Integration

### ethers.js v6
```typescript
import { ethers, Contract, BrowserProvider } from 'ethers';

async function connectAndInteract() {
  const provider = new BrowserProvider(window.ethereum);
  const signer = await provider.getSigner();

  const contract = new Contract(address, abi, signer);

  // Read (no gas)
  const balance = await contract.balanceOf(signer.address);

  // Write (sends transaction)
  const tx = await contract.transfer(recipient, ethers.parseEther("1.0"));
  const receipt = await tx.wait();

  // Listen to events
  contract.on("Transfer", (from, to, amount) => {
    console.log(`${from} → ${to}: ${ethers.formatEther(amount)} ETH`);
  });
}
```

### wagmi v2 + viem (React)
```typescript
import { useAccount, useReadContract, useWriteContract } from 'wagmi';

function TokenBalance() {
  const { address } = useAccount();
  const { data: balance } = useReadContract({
    address: contractAddress,
    abi: tokenABI,
    functionName: 'balanceOf',
    args: [address!],
  });

  const { writeContract } = useWriteContract();

  return (
    <button onClick={() =>
      writeContract({
        address: contractAddress,
        abi: tokenABI,
        functionName: 'transfer',
        args: [recipient, parseEther('1')],
      })
    }>
      Transfer (Balance: {formatEther(balance ?? 0n)})
    </button>
  );
}
```

---

## Security Checklist

- [ ] Reentrancy guards on all external calls
- [ ] Access control on all state-changing functions
- [ ] Input validation (zero address, overflow, bounds)
- [ ] Checks-Effects-Interactions pattern followed
- [ ] No `tx.origin` for auth (use `msg.sender`)
- [ ] Custom errors instead of require strings
- [ ] Events emitted for all state changes
- [ ] Tested with fuzzing (Foundry `testFuzz_`)
- [ ] Static analysis with Slither
- [ ] Gas optimization reviewed
- [ ] Upgrade safety verified (storage layout)
- [ ] External audit scheduled for mainnet deployment

---

## Key Tools

| Tool | Purpose |
|---|---|
| Foundry | Solidity testing, fuzzing, deployment |
| Hardhat | JS/TS smart contract development |
| OpenZeppelin | Audited contract libraries |
| Slither | Static analysis |
| Mythril | Symbolic execution |
| Tenderly | Transaction debugging |
| ethers.js v6 | Frontend blockchain interaction |
| wagmi v2 | React hooks for Ethereum |
| viem | Low-level TypeScript Ethereum library |
| Chainlink | Oracles, VRF, automation |
| The Graph | Blockchain data indexing |
| IPFS/Arweave | Decentralized storage |
