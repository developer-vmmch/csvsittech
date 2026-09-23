import sys
import os

with open('apps/lab/models.py', 'r') as f:
    lines = f.readlines()
    for i, line in enumerate(lines):
        if 'class InvestigationParameter' in line:
            for j in range(i, i+15):
                print(lines[j], end='')
            break
