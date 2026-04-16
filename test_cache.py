#!/usr/bin/env python
"""
Test script to verify Django cache is working correctly.
Run this with: python test_cache.py
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gate_analytics.settings')
django.setup()

from django.core.cache import cache
from django.conf import settings

print("=" * 60)
print("DJANGO CACHE DIAGNOSTIC")
print("=" * 60)

# Check cache backend
print(f"\n1. Cache Backend: {settings.CACHES['default']['BACKEND']}")
if 'LOCATION' in settings.CACHES['default']:
    print(f"   Location: {settings.CACHES['default']['LOCATION']}")

# Test cache write/read
print("\n2. Testing cache write/read:")
test_key = 'test_cache_key_12345'
test_value = {'test': 'data', 'timestamp': '2024-01-01'}

print(f"   Writing to cache: key={test_key}")
cache.set(test_key, test_value, 60)

print(f"   Reading from cache: key={test_key}")
result = cache.get(test_key)
print(f"   Result: {result}")

if result == test_value:
    print("   ✓ Cache is WORKING correctly!")
else:
    print("   ✗ Cache is NOT working - read value doesn't match written value")

# Check heartbeat key
print("\n3. Checking scanner heartbeat key:")
heartbeat_key = 'gate_staff_scanner_heartbeat_v2'
heartbeat = cache.get(heartbeat_key)
print(f"   Key: {heartbeat_key}")
print(f"   Value: {heartbeat}")

if heartbeat:
    print("   ✓ Heartbeat is ACTIVE in cache!")
else:
    print("   ✗ Heartbeat is NOT in cache (staff scanner may not be running)")

# Clean up test key
cache.delete(test_key)

print("\n" + "=" * 60)
print("DIAGNOSTIC COMPLETE")
print("=" * 60)
