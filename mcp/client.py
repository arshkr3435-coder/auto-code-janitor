from src.mcp.tools import gitlab_tools
from src.mcp.tools import mongodb_tools
from typing import Dict, Any

async def handle_agent_tool_call(function_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Interprets the tool requested by Gemini and maps it to live executions."""
    try:
        # --- GITLAB TOOL ROUTING BRANCHES ---
        if function_name == "get_repository_tree":
            return await gitlab_tools.get_repository_tree(
                project_id=arguments["project_id"],
                branch=arguments.get("branch", "main"),
                gitlab_token=arguments.get("gitlab_token")  # Forward user token
            )
            
        elif function_name in ["get_file_content", "read_file_content"]:
            return await gitlab_tools.get_file_content(
                project_id=arguments["project_id"],
                file_path=arguments["file_path"],
                branch=arguments.get("branch", "main"),
                gitlab_token=arguments.get("gitlab_token")  # Forward user token
            )
            
        elif function_name == "commit_code_changes":
            return await gitlab_tools.commit_code_changes(
                project_id=arguments["project_id"],
                branch=arguments.get("branch", "main"),
                commit_message=arguments["commit_message"],
                actions=arguments["actions"],
                gitlab_token=arguments.get("gitlab_token")  # Forward user token
            )
            
        # --- MONGODB TOOL ROUTING BRANCHES ---
        elif function_name == "query_migration_knowledgebase":
            return await mongodb_tools.query_migration_knowledgebase(
                query_string=arguments["query_string"],
                framework_context=arguments.get("framework_context"),
                mongodb_uri=arguments.get("mongodb_uri"),           # Forward database connection URI
                mongodb_database=arguments.get("mongodb_database")  # Forward target database name
            )
            
        elif function_name == "update_database_records":
            return await mongodb_tools.update_database_records(
                collection_name=arguments["collection_name"],
                filter_query=arguments["filter_query"],
                update_data=arguments["update_data"],
                mongodb_uri=arguments.get("mongodb_uri"),           # Forward database connection URI
                mongodb_database=arguments.get("mongodb_database")  # Forward target database name
            )
            
        else:
            return {"error": f"Tool '{function_name}' is not registered on this client server."}
            
    except Exception as e:
        return {"error": f"Runtime exception during tool execution: {str(e)}"}