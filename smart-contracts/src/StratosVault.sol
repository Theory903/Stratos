// SPDX-License-Identifier: MIT
pragma solidity >=0.8.20;

import "./IStratosVault.sol";

/**
 * @title StratosVault
 * @notice A simple vault for tracking portfolio value and reporting strategy changes.
 * @dev DISCLAIMER: This is a simplified vault for reporting purposes not a full ERC4626 implementation.
 */
contract StratosVault is IStratosVault {
    // State
    mapping(address => uint256) private _shares;
    uint256 private _totalShares;
    
    // In a real vault, assets would be tokens held. 
    // Here we track deposited ETH for simplicity.
    uint256 private _totalAssets;

    string public strategyDescription;
    address public manager;

    // Modifiers
    modifier onlyManager() {
        require(msg.sender == manager, "Not authorized");
        _;
    }

    constructor(string memory _description) {
        manager = msg.sender;
        strategyDescription = _description;
    }

    // --- View Functions ---

    function totalAssets() external view override returns (uint256) {
        return address(this).balance;
    }

    function userShares(address user) external view override returns (uint256) {
        return _shares[user];
    }

    function getStrategyDescription() external view override returns (string memory) {
        return strategyDescription;
    }

    // --- User Actions ---

    function deposit() external payable override returns (uint256 shares) {
        require(msg.value > 0, "Deposit must be > 0");

        uint256 assets = msg.value;
        uint256 currentTotalAssets = address(this).balance - assets; // Assets before this deposit

        if (_totalShares == 0 || currentTotalAssets == 0) {
            shares = assets;
        } else {
            shares = (assets * _totalShares) / currentTotalAssets;
        }

        _shares[msg.sender] += shares;
        _totalShares += shares;

        emit Deposit(msg.sender, assets, shares);
        return shares;
    }

    function withdraw(uint256 shares) external override returns (uint256 amount) {
        require(shares > 0, "Withdraw must be > 0");
        require(_shares[msg.sender] >= shares, "Insufficient balance");

        uint256 currentTotalAssets = address(this).balance;
        
        // Calculate amount proportional to shares
        amount = (shares * currentTotalAssets) / _totalShares;

        _shares[msg.sender] -= shares;
        _totalShares -= shares;

        // Transfer ETH
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");

        emit Withdraw(msg.sender, amount, shares);
        return amount;
    }

    // --- Manager Actions ---

    function updateDescription(string calldata description) external override onlyManager {
        strategyDescription = description;
        emit StrategyUpdated(description);
    }

    function reportRebalance(uint256 currentAssetsReported) external override onlyManager {
        // In a real vault, this might re-weight tokens.
        // Here it's a reporting hook for the off-chain oracle to signal a rebalance event.
        emit PortfolioRebalanced(block.timestamp, currentAssetsReported);
    }

    // Receive function to accept ETH
    receive() external payable {}
}
