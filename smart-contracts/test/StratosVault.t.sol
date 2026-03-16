// SPDX-License-Identifier: MIT
pragma solidity >=0.8.20;

import "forge-std/Test.sol";
import "../src/StratosVault.sol";

contract StratosVaultTest is Test {
    StratosVault vault;
    address manager = address(1);
    address user1 = address(2);
    address user2 = address(3);

    function setUp() public {
        vm.prank(manager);
        vault = new StratosVault("Alpha Strategy");
        vm.deal(user1, 100 ether);
        vm.deal(user2, 100 ether);
    }

    function testInitialState() public {
        assertEq(vault.getStrategyDescription(), "Alpha Strategy");
        assertEq(vault.totalAssets(), 0);
    }

    function testDeposit() public {
        vm.startPrank(user1);
        uint256 shares = vault.deposit{value: 10 ether}();
        vm.stopPrank();

        assertEq(shares, 10 ether); // Initial deposit implies 1:1 if totalShares represents Assets
        assertEq(vault.totalAssets(), 10 ether);
        assertEq(vault.userShares(user1), 10 ether);
    }

    function testWithdraw() public {
        // User 1 deposits
        vm.prank(user1);
        vault.deposit{value: 10 ether}();

        // User 2 deposits
        vm.prank(user2);
        vault.deposit{value: 10 ether}();

        assertEq(vault.totalAssets(), 20 ether);

        // User 1 withdraws half
        vm.prank(user1);
        vault.withdraw(5 ether);

        assertEq(vault.userShares(user1), 5 ether);
        assertEq(address(user1).balance, 95 ether); // 100 - 10 + 5
        assertEq(vault.totalAssets(), 15 ether);
    }

    function testManagerUpdate() public {
        vm.prank(manager);
        vault.updateDescription("Beta Strategy");
        assertEq(vault.getStrategyDescription(), "Beta Strategy");
    }

    function testFailNonManagerUpdate() public {
        vm.prank(user1);
        vault.updateDescription("Hacked Strategy");
    }
}
