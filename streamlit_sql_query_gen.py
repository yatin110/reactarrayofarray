import streamlit as st
import pandas as pd
import cx_Oracle
from typing import Tuple
import re

def create_connection():
    """Create and return Oracle database connection"""
    # Replace these with your actual database credentials
    connection = cx_Oracle.connect(
        user="your_username",
        password="your_password",
        dsn="your_host:1521/your_service_name"
    )
    return connection

def validate_sql(sql: str) -> bool:
    """Basic SQL validation to prevent harmful queries"""
    sql_lower = sql.lower()
    
    # Check for DML/DDL operations
    forbidden_keywords = ['insert', 'update', 'delete', 'drop', 'create', 'alter', 'truncate']
    if any(keyword in sql_lower for keyword in forbidden_keywords):
        return False
    
    # Ensure it starts with SELECT
    if not re.match(r'^\s*select', sql_lower):
        return False
        
    return True

def get_total_rows(connection, sql: str) -> int:
    """Get total number of rows for the query"""
    count_sql = f"SELECT COUNT(*) FROM ({sql})"
    with connection.cursor() as cursor:
        cursor.execute(count_sql)
        return cursor.fetchone()[0]

def fetch_page_data(connection, sql: str, offset: int, limit: int) -> pd.DataFrame:
    """Fetch a specific page of data"""
    paginated_sql = f"""
        SELECT * FROM (
            SELECT a.*, ROWNUM rnum FROM ({sql}) a WHERE ROWNUM <= {offset + limit}
        ) WHERE rnum > {offset}
    """
    
    return pd.read_sql(paginated_sql, connection)

def main():
    st.title("SQL Query Explorer")
    
    # Initialize session state variables if they don't exist
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 1
    if 'total_pages' not in st.session_state:
        st.session_state.total_pages = 0
    if 'current_df' not in st.session_state:
        st.session_state.current_df = None
    if 'filters' not in st.session_state:
        st.session_state.filters = {}
    
    # SQL Input
    sql_query = st.text_area("Enter your SQL query:", height=150)
    rows_per_page = 50
    
    if st.button("Execute Query"):
        if not sql_query:
            st.error("Please enter a SQL query.")
            return
            
        if not validate_sql(sql_query):
            st.error("Invalid or unauthorized SQL query. Only SELECT statements are allowed.")
            return
            
        try:
            connection = create_connection()
            
            # Get total rows and calculate total pages
            total_rows = get_total_rows(connection, sql_query)
            st.session_state.total_pages = (total_rows + rows_per_page - 1) // rows_per_page
            
            # Reset to first page
            st.session_state.current_page = 1
            
            # Fetch first page
            offset = (st.session_state.current_page - 1) * rows_per_page
            st.session_state.current_df = fetch_page_data(connection, sql_query, offset, rows_per_page)
            
            connection.close()
            
        except Exception as e:
            st.error(f"Error executing query: {str(e)}")
            return
    
    # Display data and controls if we have a dataframe
    if st.session_state.current_df is not None:
        # Add filters for each column
        st.subheader("Filters")
        cols = st.columns(3)
        current_col = 0
        
        for column in st.session_state.current_df.columns:
            with cols[current_col]:
                if column in st.session_state.filters:
                    filter_value = st.text_input(f"Filter {column}", st.session_state.filters[column])
                else:
                    filter_value = st.text_input(f"Filter {column}")
                
                if filter_value:
                    st.session_state.filters[column] = filter_value
                elif column in st.session_state.filters:
                    del st.session_state.filters[column]
            
            current_col = (current_col + 1) % 3
        
        # Apply filters
        filtered_df = st.session_state.current_df.copy()
        for column, filter_value in st.session_state.filters.items():
            filtered_df = filtered_df[filtered_df[column].astype(str).str.contains(filter_value, case=False, na=False)]
        
        # Display the filtered dataframe
        st.dataframe(filtered_df)
        
        # Pagination controls
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col1:
            if st.button("Previous", disabled=st.session_state.current_page <= 1):
                st.session_state.current_page -= 1
                
                # Fetch previous page
                connection = create_connection()
                offset = (st.session_state.current_page - 1) * rows_per_page
                st.session_state.current_df = fetch_page_data(connection, sql_query, offset, rows_per_page)
                connection.close()
                st.rerun()
        
        with col2:
            st.write(f"Page {st.session_state.current_page} of {st.session_state.total_pages}")
        
        with col3:
            if st.button("Next", disabled=st.session_state.current_page >= st.session_state.total_pages):
                st.session_state.current_page += 1
                
                # Fetch next page
                connection = create_connection()
                offset = (st.session_state.current_page - 1) * rows_per_page
                st.session_state.current_df = fetch_page_data(connection, sql_query, offset, rows_per_page)
                connection.close()
                st.rerun()

if __name__ == "__main__":
    main()
