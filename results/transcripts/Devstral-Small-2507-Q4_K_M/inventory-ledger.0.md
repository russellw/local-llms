# inventory-ledger -- FIFO inventory ledger with fractional unit costs

passed: False   stopped: no_call   steps: 2/26   edits: 0   test runs: 0   failing at end: 10/14

## step 1

I'll help you debug the inventory ledger project. Let's start by exploring the project structure and understanding the code.

First, let's list the files in the project directory:

```
!ls -la
```

Now, let's examine the content of the main Python files to understand the structure and functionality of the inventory ledger. I'll start with the main module:

```
!cat inventory_ledger.py
```

Next, let's look at any other relevant files that might be part of the project:

```
!cat __init__.py
!cat tests.py
```

Now that we have an understanding of the code, let's run the tests to see what's failing:

```
!python -m unittest discover
```

Based on the test failures, we can identify the issues in the inventory ledger code. Let's make the necessary changes to fix the failing tests.

For example, if we find that the `add_item` function is not working correctly, we can modify it like this:

```
replace_in_file('inventory_ledger.py', 'def add_item(self, item):\n        self.items.append(item)', 'def add_item(self, item):\n        if item not in self.items:\n            self.items.append(item)')
```

After making the changes, let's run the tests again to verify that our fixes resolved the issues:

```
!python -m unittest discover
```

Once all the tests pass, we can call the `finish` function to complete the task:

```
finish()
```

## step 2

I apologize for the confusion. Let's start by listing the files in the project directory to understand its structure:

```
!ls -la
```
