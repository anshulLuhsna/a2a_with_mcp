#!/usr/bin/env python3
"""
Test script for the financial agent with MCP integration.
"""
import asyncio
import os
import json
from datetime import datetime
from financial_agent_langgraph.agent import process_financial_task
from financial_agent_langgraph.common.types import Task, Message, TextPart, TaskState, TaskStatus

def create_test_task(query_text: str) -> Task:
    """Create a test task with the given query text."""
    return Task(
        id="test-task-" + datetime.now().strftime("%Y%m%d%H%M%S"),
        sessionId="test-session",
        history=[
            Message(
                role="user",
                parts=[TextPart(text=query_text)]
            )
        ],
        status=TaskStatus(
            state=TaskState.IN_PROGRESS,
            timestamp=datetime.now()
        ),
        metadata={}
    )

def main():
    """Run a test of the financial agent with MCP integration."""
    # Sample financial queries to test
    test_queries = [
        "What's the latest financial snapshot data?",
        "Show me financial data from the database",
        "Run a SQL query to get all users from the database",
    ]
    
    print("Starting financial agent test with MCP integration")
    
    for i, query in enumerate(test_queries):
        print(f"\n=== Test Query {i+1}: {query} ===")
        
        # Create a test task
        task = create_test_task(query)
        print(f"Created task {task.id}")
        
        # Process the task
        print("Processing task...")
        result = process_financial_task(task)
        
        # Display the result
        print("\nAgent Response:")
        if result.status.message and result.status.message.parts:
            for part in result.status.message.parts:
                if hasattr(part, 'text'):
                    print(part.text)
        else:
            print("No response message found")
        
        print("\nTask Status:", result.status.state)
        
        # Display artifacts if any
        if result.artifacts:
            print("\nArtifacts:")
            for artifact in result.artifacts:
                print(f"- {artifact.name}: {artifact.description}")
        
        print("\n" + "="*50)

if __name__ == "__main__":
    main() 