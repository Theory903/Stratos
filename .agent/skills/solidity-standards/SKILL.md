---
name: solidity-standards
description: Solidity 0.8.20+ standards — security patterns, gas optimization, testing with Foundry/Hardhat, upgradability, and Web3 development practices
---

# Solidity Standards

## Version & Tooling
- **Solidity**: 0.8.20+
- **Frameworks**: Foundry (preferred) or Hardhat
- **Libraries**: OpenZeppelin Contracts
- **Testing**: Forge (Foundry) or Mocha (Hardhat)

---

## Project Structure

### Foundry
```
src/
├── interfaces/
├── libraries/
└── contracts/
test/
├── unit/
└── integration/
script/
└── Deploy.s.sol
foundry.toml
```

### Hardhat
```
contracts/
├── interfaces/
├── libraries/
├── tokens/
└── governance/
scripts/deploy/
test/
hardhat.config.ts
```

---

## Security Rules (Critical)

### 1. Reentrancy Protection
Always use Checks-Effects-Interactions pattern + ReentrancyGuard:
```solidity
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

contract Vault is ReentrancyGuard {
    mapping(address => uint256) public balances;

    function withdraw(uint256 amount) external nonReentrant {
        // CHECKS
        require(balances[msg.sender] >= amount, "Insufficient");
        // EFFECTS
        balances[msg.sender] -= amount;
        // INTERACTIONS
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "Transfer failed");
    }
}
```

### 2. Access Control
Use OpenZeppelin's AccessControl or Ownable. Never roll custom access control without audit.
```solidity
import "@openzeppelin/contracts/access/AccessControl.sol";

contract MyContract is AccessControl {
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    constructor() { _grantRole(DEFAULT_ADMIN_ROLE, msg.sender); }
    function mint(address to, uint256 amt) external onlyRole(MINTER_ROLE) { }
}
```

### 3. Integer Safety
Solidity 0.8.0+ has built-in overflow/underflow checks. Use `unchecked` only when mathematically proven safe.

### 4. Front-Running Protection
- Use commit-reveal for sensitive operations.
- Use time-locks for governance.
- Use deadline parameters for DEX-like operations.

### 5. Oracle Manipulation
- Use Chainlink for price feeds (decentralized).
- Use TWAP (time-weighted average price).
- Never rely on single block spot prices.

### 6. Flash Loan Protection
- Check invariants at end of transaction.
- Use reentrancy guards.
- Add time-locks for critical operations.

---

## Gas Optimization

```solidity
contract GasOptimized {
    // Pack storage: fit multiple vars in 32 bytes
    uint128 public value1;    // slot 0 (first half)
    uint128 public value2;    // slot 0 (second half)

    // Use calldata for read-only external params
    function process(uint256[] calldata data) external pure returns (uint256) {
        uint256 sum;
        uint256 length = data.length;  // Cache length

        unchecked {  // Safe when no overflow possible
            for (uint256 i; i < length; ++i) {
                sum += data[i];
            }
        }
        return sum;
    }
}
```

**Rules:**
- Use `calldata` instead of `memory` for read-only external params.
- Pack storage variables to minimize slots.
- Cache storage reads in local variables.
- Use `unchecked` blocks when overflow is impossible.
- Prefer `++i` over `i++`.
- Use custom errors instead of require strings.
- Short-circuit conditions: cheapest checks first.

---

## Custom Errors & Events

```solidity
// Custom errors (gas-efficient)
error InsufficientBalance(uint256 requested, uint256 available);
error Unauthorized(address caller);

contract MyContract {
    event Deposit(address indexed user, uint256 amount);
    event Withdrawal(address indexed user, uint256 amount);

    function withdraw(uint256 amount) external {
        if (balances[msg.sender] < amount) {
            revert InsufficientBalance(amount, balances[msg.sender]);
        }
        balances[msg.sender] -= amount;
        emit Withdrawal(msg.sender, amount);
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "Transfer failed");
    }
}
```

---

## NatSpec Documentation

```solidity
/// @title Staking Pool
/// @author STRATOS Team
/// @notice Allows users to stake tokens and earn rewards
/// @dev Uses OpenZeppelin ReentrancyGuard for reentrancy protection
contract StakingPool {
    /// @notice Stakes tokens into the pool
    /// @dev Transfers tokens from caller, updates internal accounting
    /// @param amount Amount of tokens to stake (must be > 0)
    /// @return sharesMinted Number of pool shares issued
    function stake(uint256 amount) external returns (uint256 sharesMinted) { }
}
```

---

## Upgradability

### UUPS Pattern (preferred)
```solidity
import "@openzeppelin/contracts-upgradeable/proxy/utils/Initializable.sol";
import "@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/access/OwnableUpgradeable.sol";

contract MyContractV1 is Initializable, UUPSUpgradeable, OwnableUpgradeable {
    uint256 public value;
    uint256[49] private __gap;  // Storage gap for future variables

    /// @custom:oz-upgrades-unsafe-allow constructor
    constructor() { _disableInitializers(); }

    function initialize() public initializer {
        __Ownable_init(msg.sender);
        __UUPSUpgradeable_init();
    }

    function _authorizeUpgrade(address) internal override onlyOwner {}
}
```

**Rules:**
- Never change existing storage slot layout.
- Use `initializer` instead of constructor.
- Add storage gaps (`uint256[50] private __gap`) for future variables.
- Test upgrades with OpenZeppelin's upgrade plugin.

---

## Testing (Foundry)

```solidity
// test/MyContract.t.sol
pragma solidity ^0.8.20;
import "forge-std/Test.sol";
import "../src/MyContract.sol";

contract MyContractTest is Test {
    MyContract public target;
    address public alice = makeAddr("alice");

    function setUp() public {
        target = new MyContract();
    }

    function testDeposit() public {
        vm.deal(alice, 1 ether);
        vm.prank(alice);
        target.deposit{value: 1 ether}();
        assertEq(target.balances(alice), 1 ether);
    }

    function testFuzz_Deposit(uint256 amount) public {
        vm.assume(amount > 0 && amount < 100 ether);
        vm.deal(alice, amount);
        vm.prank(alice);
        target.deposit{value: amount}();
        assertEq(target.balances(alice), amount);
    }

    function testRevert_WithdrawInsufficientBalance() public {
        vm.prank(alice);
        vm.expectRevert(abi.encodeWithSelector(
            InsufficientBalance.selector, 1 ether, 0
        ));
        target.withdraw(1 ether);
    }
}
```

**Coverage minimum: 90% for production contracts.**

---

## Frontend Integration

### ethers.js v6
```typescript
const provider = new ethers.BrowserProvider(window.ethereum);
const signer = await provider.getSigner();
const contract = new ethers.Contract(address, abi, signer);
const tx = await contract.transfer(recipient, amount);
await tx.wait();
```

### wagmi v2 (React)
```typescript
const { data } = useReadContract({
  address: contractAddress,
  abi: contractABI,
  functionName: 'balanceOf',
  args: [userAddress],
});
```

---

## Key Libraries

| Library | Purpose |
|---|---|
| OpenZeppelin Contracts | Audited token standards, access control, security |
| Foundry (forge) | Fast Solidity testing, fuzzing |
| Hardhat | JS/TS testing, deployment scripts |
| Chainlink | Oracles, VRF, automation |
| ethers.js v6 | Frontend contract interaction |
| wagmi v2 | React hooks for Ethereum |
| Slither | Static analysis security tool |
| Mythril | Symbolic execution security |
