import streamlit as st
import cx_Oracle
import pandas as pd
from typing import List, Dict, Tuple, Optional

# Database connection parameters
DB_CONFIG = {
    "user": "username",
    "password": "password",
    "dsn": "hostname:port/service_name"
}

def get_db_connection():
    try:
        conn = cx_Oracle.connect(
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            dsn=DB_CONFIG["dsn"]
        )
        return conn
    except Exception as e:
        st.error(f"Database connection error: {str(e)}")
        return None

def get_tables() -> List[str]:
    conn = get_db_connection()
    if not conn:
        return []
    
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT table_name FROM user_tables ORDER BY table_name")
        tables = [row[0] for row in cursor.fetchall()]
        return tables
    except Exception as e:
        st.error(f"Error fetching tables: {str(e)}")
        return []
    finally:
        cursor.close()
        conn.close()

def get_columns(table_name: str) -> List[str]:
    conn = get_db_connection()
    if not conn:
        return []
    
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT column_name, data_type FROM user_tab_columns WHERE table_name = '{table_name}' ORDER BY column_id")
        columns = [(row[0], row[1]) for row in cursor.fetchall()]
        return columns
    except Exception as e:
        st.error(f"Error fetching columns: {str(e)}")
        return []
    finally:
        cursor.close()
        conn.close()

def get_parent_templates() -> List[Dict]:
    conn = get_db_connection()
    if not conn:
        return []
    
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT template_id, template_name, query FROM sql_templates WHERE template_type = 'PARENT'")
        templates = [{"id": row[0], "name": row[1], "query": row[2]} for row in cursor.fetchall()]
        return templates
    except Exception as e:
        st.error(f"Error fetching parent templates: {str(e)}")
        return []
    finally:
        cursor.close()
        conn.close()

def get_all_templates() -> List[Dict]:
    conn = get_db_connection()
    if not conn:
        return []
    
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT template_id, template_name, template_type, query FROM sql_templates ORDER BY template_type, template_name")
        templates = [{"id": row[0], "name": row[1], "type": row[2], "query": row[3]} for row in cursor.fetchall()]
        return templates
    except Exception as e:
        st.error(f"Error fetching templates: {str(e)}")
        return []
    finally:
        cursor.close()
        conn.close()

def get_template_by_id(template_id: int) -> Optional[Dict]:
    conn = get_db_connection()
    if not conn:
        return None
    
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT template_id, template_name, template_type, query, template_data FROM sql_templates WHERE template_id = :id", 
                      {"id": template_id})
        row = cursor.fetchone()
        if row:
            return {"id": row[0], "name": row[1], "type": row[2], "query": row[3], "data": row[4]}
        return None
    except Exception as e:
        st.error(f"Error fetching template: {str(e)}")
        return None
    finally:
        cursor.close()
        conn.close()

def save_template(template_name: str, template_type: str, query: str, template_data: str, parent_id: Optional[int] = None) -> bool:
    conn = get_db_connection()
    if not conn:
        return False
    
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO sql_templates (template_name, template_type, query, template_data, parent_id) VALUES (:name, :type, :query, :data, :parent_id)",
            {"name": template_name, "type": template_type, "query": query, "data": template_data, "parent_id": parent_id}
        )
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"Error saving template: {str(e)}")
        return False
    finally:
        cursor.close()
        conn.close()

def update_template(template_id: int, template_name: str, query: str, template_data: str) -> bool:
    conn = get_db_connection()
    if not conn:
        return False
    
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE sql_templates SET template_name = :name, query = :query, template_data = :data WHERE template_id = :id",
            {"name": template_name, "query": query, "data": template_data, "id": template_id}
        )
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"Error updating template: {str(e)}")
        return False
    finally:
        cursor.close()
        conn.close()

def generate_parent_query(selected_tables: List[str], joins: List[Dict], selected_columns: List[Dict], 
                          aggregations: Dict, group_by_columns: List[str], where_conditions: List[str]) -> str:
    if not selected_tables:
        return ""
    
    # Process columns with aggregations
    columns_sql = []
    for col in selected_columns:
        table = col["table"]
        column = col["column"]
        alias = f"{table}_{column}"
        
        if column in aggregations and aggregations[column]:
            agg_func = aggregations[column]
            columns_sql.append(f"{agg_func}({table}.{column}) AS {alias}")
        else:
            columns_sql.append(f"{table}.{column} AS {alias}")
    
    # Generate FROM clause
    from_clause = selected_tables[0]
    
    # Generate JOIN clause
    join_clause = ""
    for join in joins:
        join_clause += f" JOIN {join['right_table']} ON {join['left_table']}.{join['left_column']} = {join['right_table']}.{join['right_column']}"
    
    # Generate WHERE clause
    where_clause = ""
    if where_conditions:
        where_clause = " WHERE " + " AND ".join(where_conditions)
    
    # Generate GROUP BY clause
    group_by_clause = ""
    if group_by_columns:
        group_by_clause = " GROUP BY " + ", ".join(group_by_columns)
    
    # Combine all parts into final query
    query = f"SELECT {', '.join(columns_sql)} FROM {from_clause}{join_clause}{where_clause}{group_by_clause}"
    
    return query

def generate_child_query(parent_query: str, selected_parent_columns: List[str], child_where_conditions: List[str]) -> str:
    if not parent_query:
        return ""
    
    # Create a subquery from the parent query
    subquery = f"({parent_query}) parent_data"
    
    # Process columns
    columns_sql = []
    for col in selected_parent_columns:
        columns_sql.append(f"parent_data.{col}")
    
    # Generate WHERE clause
    where_clause = ""
    if child_where_conditions:
        where_clause = " WHERE " + " AND ".join(child_where_conditions)
    
    # Combine all parts into final query
    query = f"SELECT {', '.join(columns_sql)} FROM {subquery}{where_clause}"
    
    return query

def create_parent_template():
    st.subheader("Create Parent Template")
    
    template_name = st.text_input("Template Name")
    
    # Table selection
    tables = get_tables()
    selected_tables = st.multiselect("Select Tables", tables)
    
    # Initialize session state for joins if not already initialized
    if "joins" not in st.session_state:
        st.session_state.joins = []
    
    # Show join builder if at least two tables are selected
    if len(selected_tables) >= 2:
        st.subheader("Define Joins")
        
        col1, col2, col3, col4, col5 = st.columns([2, 2, 1, 2, 1])
        with col1:
            left_table = st.selectbox("Left Table", selected_tables, key="join_left_table")
        with col2:
            left_columns = [col[0] for col in get_columns(left_table)]
            left_column = st.selectbox("Left Column", left_columns, key="join_left_column")
        with col3:
            st.markdown("### =")
        with col4:
            right_table = st.selectbox("Right Table", selected_tables, key="join_right_table")
        with col5:
            right_columns = [col[0] for col in get_columns(right_table)]
            right_column = st.selectbox("Right Column", right_columns, key="join_right_column")
        
        if st.button("Add Join"):
            join = {
                "left_table": left_table,
                "left_column": left_column,
                "right_table": right_table,
                "right_column": right_column
            }
            st.session_state.joins.append(join)
    
    # Display current joins
    if st.session_state.joins:
        st.subheader("Current Joins")
        for i, join in enumerate(st.session_state.joins):
            st.write(f"{join['left_table']}.{join['left_column']} = {join['right_table']}.{join['right_column']}")
            if st.button(f"Remove Join {i+1}"):
                st.session_state.joins.pop(i)
                st.experimental_rerun()
    
    # Column selection
    st.subheader("Select Columns and Aggregations")
    
    # Initialize selected columns if not already initialized
    if "selected_columns" not in st.session_state:
        st.session_state.selected_columns = []
    
    # Show columns from all selected tables
    all_columns = []
    for table in selected_tables:
        cols = get_columns(table)
        for col in cols:
            all_columns.append({"table": table, "column": col[0], "data_type": col[1]})
    
    # Display column selection interface
    for idx, col_info in enumerate(all_columns):
        col1, col2, col3 = st.columns([3, 2, 1])
        with col1:
            include = st.checkbox(f"{col_info['table']}.{col_info['column']} ({col_info['data_type']})", key=f"col_{idx}")
        with col2:
            agg_options = ["", "SUM", "AVG", "COUNT", "MAX", "MIN"]
            agg = st.selectbox("Aggregation", agg_options, key=f"agg_{idx}")
        with col3:
            group_by = st.checkbox("Group By", key=f"group_{idx}")
        
        if include:
            existing = next((c for c in st.session_state.selected_columns if c["table"] == col_info["table"] and c["column"] == col_info["column"]), None)
            if not existing:
                col_data = {
                    "table": col_info["table"],
                    "column": col_info["column"],
                    "data_type": col_info["data_type"],
                    "aggregation": agg,
                    "group_by": group_by
                }
                st.session_state.selected_columns.append(col_data)
            else:
                existing["aggregation"] = agg
                existing["group_by"] = group_by
        else:
            st.session_state.selected_columns = [c for c in st.session_state.selected_columns 
                                               if not (c["table"] == col_info["table"] and c["column"] == col_info["column"])]
    
    # Where conditions
    st.subheader("Where Conditions")
    
    # Initialize where conditions if not already initialized
    if "where_conditions" not in st.session_state:
        st.session_state.where_conditions = []
    
    col1, col2, col3 = st.columns([3, 2, 3])
    with col1:
        if st.session_state.selected_columns:
            column_options = [f"{c['table']}.{c['column']}" for c in st.session_state.selected_columns]
            where_column = st.selectbox("Column", column_options, key="where_column")
        else:
            where_column = st.selectbox("Column", ["No columns selected"], disabled=True)
    with col2:
        operators = ["=", "<>", ">", "<", ">=", "<=", "LIKE", "IN", "NOT IN", "IS NULL", "IS NOT NULL"]
        where_operator = st.selectbox("Operator", operators, key="where_operator")
    with col3:
        if where_operator in ["IS NULL", "IS NOT NULL"]:
            where_value = ""
        else:
            where_value = st.text_input("Value", key="where_value")
    
    if st.button("Add Condition"):
        if where_operator in ["IS NULL", "IS NOT NULL"]:
            condition = f"{where_column} {where_operator}"
        else:
            condition = f"{where_column} {where_operator} {where_value}"
        st.session_state.where_conditions.append(condition)
    
    # Display current where conditions
    if st.session_state.where_conditions:
        st.subheader("Current Where Conditions")
        for i, condition in enumerate(st.session_state.where_conditions):
            st.write(condition)
            if st.button(f"Remove Condition {i+1}"):
                st.session_state.where_conditions.pop(i)
                st.experimental_rerun()
    
    # Generate query button
    if st.button("Generate Query"):
        if not template_name:
            st.error("Please provide a template name")
        elif not selected_tables:
            st.error("Please select at least one table")
        elif not st.session_state.selected_columns:
            st.error("Please select at least one column")
        else:
            # Prepare data for query generation
            selected_columns_for_query = [{"table": col["table"], "column": col["column"]} for col in st.session_state.selected_columns]
            aggregations = {col["column"]: col["aggregation"] for col in st.session_state.selected_columns if col["aggregation"]}
            group_by_columns = [f"{col['table']}.{col['column']}" for col in st.session_state.selected_columns if col["group_by"]]
            
            # Generate query
            query = generate_parent_query(
                selected_tables, 
                st.session_state.joins, 
                selected_columns_for_query, 
                aggregations, 
                group_by_columns, 
                st.session_state.where_conditions
            )
            
            st.session_state.current_query = query
            st.session_state.current_template_name = template_name
            st.session_state.current_template_type = "PARENT"
            
            # Prepare template data for saving
            template_data = {
                "tables": selected_tables,
                "joins": st.session_state.joins,
                "columns": st.session_state.selected_columns,
                "where_conditions": st.session_state.where_conditions
            }
            
            st.session_state.current_template_data = str(template_data)
            
            # Show the generated query
            st.subheader("Generated SQL Query")
            st.code(query, language="sql")
            
            # Save template button
            if st.button("Save Template"):
                success = save_template(
                    template_name=template_name,
                    template_type="PARENT",
                    query=query,
                    template_data=str(template_data)
                )
                
                if success:
                    st.success(f"Template '{template_name}' saved successfully!")
                    # Reset state
                    st.session_state.joins = []
                    st.session_state.selected_columns = []
                    st.session_state.where_conditions = []
                    st.session_state.current_query = ""
                    st.session_state.current_template_name = ""
                    st.session_state.current_template_type = ""
                    st.session_state.current_template_data = ""

def create_child_template():
    st.subheader("Create Child Template")
    
    template_name = st.text_input("Child Template Name")
    
    # Parent template selection
    parent_templates = get_parent_templates()
    parent_template_names = [t["name"] for t in parent_templates]
    
    selected_parent = st.selectbox("Select Parent Template", parent_template_names)
    
    # Get selected parent template details
    selected_parent_id = None
    parent_query = ""
    
    for template in parent_templates:
        if template["name"] == selected_parent:
            selected_parent_id = template["id"]
            parent_query = template["query"]
            break
    
    if parent_query:
        # Execute the parent query to get columns
        conn = get_db_connection()
        if conn:
            try:
                # Just fetch metadata without executing
                cursor = conn.cursor()
                cursor.execute(f"SELECT * FROM ({parent_query}) WHERE 1=0")
                
                # Get column names from cursor description
                parent_columns = [col[0] for col in cursor.description]
                
                # Column selection from parent
                st.subheader("Select Columns from Parent Template")
                selected_parent_columns = st.multiselect("Columns", parent_columns)
                
                # Where conditions
                st.subheader("Additional Where Conditions")
                
                # Initialize where conditions if not already initialized
                if "child_where_conditions" not in st.session_state:
                    st.session_state.child_where_conditions = []
                
                col1, col2, col3 = st.columns([3, 2, 3])
                with col1:
                    where_column = st.selectbox("Column", parent_columns, key="child_where_column")
                with col2:
                    operators = ["=", "<>", ">", "<", ">=", "<=", "LIKE", "IN", "NOT IN", "IS NULL", "IS NOT NULL"]
                    where_operator = st.selectbox("Operator", operators, key="child_where_operator")
                with col3:
                    if where_operator in ["IS NULL", "IS NOT NULL"]:
                        where_value = ""
                    else:
                        where_value = st.text_input("Value", key="child_where_value")
                
                if st.button("Add Condition"):
                    if where_operator in ["IS NULL", "IS NOT NULL"]:
                        condition = f"{where_column} {where_operator}"
                    else:
                        condition = f"{where_column} {where_operator} {where_value}"
                    st.session_state.child_where_conditions.append(condition)
                
                # Display current where conditions
                if st.session_state.child_where_conditions:
                    st.subheader("Current Where Conditions")
                    for i, condition in enumerate(st.session_state.child_where_conditions):
                        st.write(condition)
                        if st.button(f"Remove Child Condition {i+1}"):
                            st.session_state.child_where_conditions.pop(i)
                            st.experimental_rerun()
                
                # Generate query button
                if st.button("Generate Child Query"):
                    if not template_name:
                        st.error("Please provide a template name")
                    elif not selected_parent_columns:
                        st.error("Please select at least one column from parent template")
                    else:
                        # Generate child query
                        child_query = generate_child_query(
                            parent_query,
                            selected_parent_columns,
                            st.session_state.child_where_conditions
                        )
                        
                        st.session_state.current_query = child_query
                        st.session_state.current_template_name = template_name
                        st.session_state.current_template_type = "CHILD"
                        
                        # Prepare template data for saving
                        template_data = {
                            "parent_id": selected_parent_id,
                            "parent_name": selected_parent,
                            "columns": selected_parent_columns,
                            "where_conditions": st.session_state.child_where_conditions
                        }
                        
                        st.session_state.current_template_data = str(template_data)
                        
                        # Show the generated query
                        st.subheader("Generated SQL Query")
                        st.code(child_query, language="sql")
                        
                        # Save template button
                        if st.button("Save Child Template"):
                            success = save_template(
                                template_name=template_name,
                                template_type="CHILD",
                                query=child_query,
                                template_data=str(template_data),
                                parent_id=selected_parent_id
                            )
                            
                            if success:
                                st.success(f"Child template '{template_name}' saved successfully!")
                                # Reset state
                                st.session_state.child_where_conditions = []
                                st.session_state.current_query = ""
                                st.session_state.current_template_name = ""
                                st.session_state.current_template_type = ""
                                st.session_state.current_template_data = ""
            
            except Exception as e:
                st.error(f"Error: {str(e)}")
            finally:
                cursor.close()
                conn.close()

def edit_template():
    st.subheader("Edit Template")
    
    # Get all templates
    templates = get_all_templates()
    template_options = [f"{t['name']} ({t['type']})" for t in templates]
    
    selected_template_option = st.selectbox("Select Template to Edit", template_options)
    
    if selected_template_option:
        # Get template ID
        template_idx = template_options.index(selected_template_option)
        template_id = templates[template_idx]["id"]
        
        # Fetch template details
        template = get_template_by_id(template_id)
        
        if template:
            # Display template details
            st.write(f"Template Type: {template['type']}")
            
            # Edit template name
            new_template_name = st.text_input("Template Name", value=template["name"])
            
            # Show query
            st.subheader("Current SQL Query")
            st.code(template["query"], language="sql")
            
            # Edit query - simplified for this example
            # In a full application, you would recreate the template editing UI based on template_data
            new_query = st.text_area("Edit SQL Query", value=template["query"], height=200)
            
            if st.button("Update Template"):
                # Update the template
                success = update_template(
                    template_id=template_id,
                    template_name=new_template_name,
                    query=new_query,
                    template_data=template["data"]
                )
                
                if success:
                    st.success(f"Template '{new_template_name}' updated successfully!")

def view_templates():
    st.subheader("View Templates")
    
    # Get all templates
    templates = get_all_templates()
    
    # Create a table of templates
    template_df = pd.DataFrame([
        {"ID": t["id"], "Name": t["name"], "Type": t["type"]} 
        for t in templates
    ])
    
    if not template_df.empty:
        st.dataframe(template_df)
        
        # Select a template to view
        template_id = st.number_input("Enter Template ID to View", min_value=1, step=1)
        
        if st.button("View Template"):
            template = get_template_by_id(template_id)
            
            if template:
                st.subheader(f"Template: {template['name']} ({template['type']})")
                st.code(template["query"], language="sql")
                
                # Execute query button
                if st.button("Execute Query"):
                    conn = get_db_connection()
                    if conn:
                        try:
                            cursor = conn.cursor()
                            cursor.execute(template["query"])
                            
                            # Fetch a limited number of rows
                            rows = cursor.fetchmany(100)
                            
                            if rows:
                                # Convert to DataFrame for display
                                columns = [col[0] for col in cursor.description]
                                result_df = pd.DataFrame(rows, columns=columns)
                                
                                st.subheader("Query Results (First 100 rows)")
                                st.dataframe(result_df)
                            else:
                                st.info("Query returned no results")
                        
                        except Exception as e:
                            st.error(f"Error executing query: {str(e)}")
                        finally:
                            cursor.close()
                            conn.close()
    else:
        st.info("No templates found")

def main():
    st.title("SQL Template Manager")
    
    # Create sidebar for navigation
    st.sidebar.title("Navigation")
    app_mode = st.sidebar.radio("Select Mode", 
                               ["Create Template", "Edit Template", "View Templates"])
    
    # Initialize session state variables if they don't exist
    if "current_query" not in st.session_state:
        st.session_state.current_query = ""
    if "current_template_name" not in st.session_state:
        st.session_state.current_template_name = ""
    if "current_template_type" not in st.session_state:
        st.session_state.current_template_type = ""
    if "current_template_data" not in st.session_state:
        st.session_state.current_template_data = ""
    
    # Display the selected mode
    if app_mode == "Create Template":
        # Ask if parent or child template
        template_type = st.radio("Select Template Type", ["Parent Template", "Child Template"])
        
        if template_type == "Parent Template":
            create_parent_template()
        else:
            create_child_template()
    
    elif app_mode == "Edit Template":
        edit_template()
    
    else:  # View Templates
        view_templates()

if __name__ == "__main__":
    main()
