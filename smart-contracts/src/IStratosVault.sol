// SPDX-License-Identifier: MIT
pragma solidity >=0.8.20;

/**
 * @title IStratosVault
 * @notice Simplified interface for Stratos Portfolio Reporting and Management
 */
interface IStratosVault {
    // Events
    event Deposit(address indexed user, uint256 amount, uint256 shares);
    event Withdraw(address indexed user, uint256 amount, uint256 shares);
    event StrategyUpdated(string newDescription);
    event PortfolioRebalanced(uint256 timestamp, uint256 totalAssets);

    // View Functions
    function totalAssets() external view returns (uint256);
    function userShares(address user) external view returns (uint256);
    function getStrategyDescription() external view returns (string memory);

    // Write Functions
    function deposit() external payable returns (uint256 shares);
    function withdraw(uint256 shares) external returns (uint256 amount);
    
    // Only Strategy Manager
    function updateDescription(string calldata description) external;
    function reportRebalance(uint256 currentAssets) external;
}
