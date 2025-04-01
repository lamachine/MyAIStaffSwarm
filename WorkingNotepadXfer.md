## Main Graph Enhancement Plan (2024-03-xx)

### Original Request
Align `main_graph.py` with `AgentSupervisorGraphTemplate.py` structure and best practices, focusing on:
- Modularizing code
- Implementing proper logging/debugging
- Standardizing state management
- Adding tool integration framework
- Improving message routing

### Current Structure Analysis of main_graph.py
1. Basic state management with `AgentState`
2. Simple graph with just Ronan (orchestrator) and end nodes
3. Minimal imports and setup
4. No logging or debugging infrastructure
5. No tool integration yet

### Initial Enhancement Suggestions

1. **Enhanced State Management**
```python
class MainGraphState(TypedDict, total=False):
    session_id: str
    timestamp: str
    sender: str  # Values: "Ronan", "tool", "ui", etc
    target: str  # Next node to process
    content: str # Current message content
    context: dict  # Contextual information
    tool_states: dict  # Tool-specific states
    messages: Annotated[Sequence[BaseMessage], add_messages]
    metadata: dict  # Additional metadata
```

2. **Logging Infrastructure**
- Move logging to core module
- Implement custom formatter
- Add comprehensive debug logging
- Track message flow and state changes

3. **Enhanced Graph Structure**
- Improved node organization
- Better error handling
- State persistence
- Message routing logic
- Tool integration framework

### Next Steps to Consider
1. Tool integration framework
2. Message routing logic
3. UI node integration
4. State persistence with Supabase
5. Error handling middleware

### Benefits
- More maintainable code structure
- Better debugging capabilities
- Clearer message flow
- Improved error handling
- Easier to add new functionality
