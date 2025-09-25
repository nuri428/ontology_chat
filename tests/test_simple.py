"""Simple test to verify pytest setup."""

import pytest


def test_basic_math():
    """Test basic math operations."""
    assert 2 + 2 == 4
    assert 3 * 3 == 9
    assert 10 / 2 == 5


def test_string_operations():
    """Test string operations."""
    assert "hello" + " " + "world" == "hello world"
    assert "PYTHON".lower() == "python"
    assert len("test") == 4


@pytest.mark.asyncio
async def test_async_function():
    """Test async function execution."""
    import asyncio

    async def async_add(a, b):
        await asyncio.sleep(0.01)
        return a + b

    result = await async_add(1, 2)
    assert result == 3


class TestClass:
    """Test class example."""

    def test_in_class(self):
        """Test method in class."""
        assert True

    def test_list_operations(self):
        """Test list operations."""
        test_list = [1, 2, 3]
        test_list.append(4)
        assert len(test_list) == 4
        assert test_list[-1] == 4