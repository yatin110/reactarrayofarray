import streamlit as st
from sqlalchemy import create_engine, text
import pandas as pd

# Function to establish Oracle DB connection
def create_db_engine(username, password, host, port, service_name):
    try:
        dsn = f"oracle+cx_oracle://{username}:{password}@{host}:{port}/?service_name={service_name}"
        engine = create_engine(dsn)
        return engine
    except Exception as e:
        st.error(f"Error connecting to database: {str(e)}")
        return None

# Function to fetch table and column metadata
def fetch_metadata(engine):
    try:
        with engine.connect() as conn:
            tables_query = "SELECT table_name FROM user_tables"
            tables = pd.read_sql(tables_query, conn)

            columns_query = "SELECT table_name, column_name FROM user_tab_columns"
            columns = pd.read_sql(columns_query, conn)

            return tables, columns
    except Exception as e:
        st.error(f"Error fetching metadata: {str(e)}")
        return None, None

# Main application
def main():
    st.title("Drag-and-Drop SQL Query Builder for Oracle")

    # Database connection configuration
    with st.sidebar:
        st.header("Database Configuration")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        host = st.text_input("Host")
        port = st.text_input("Port", value="1521")
        service_name = st.text_input("Service Name")

        if st.button("Connect"):
            engine = create_db_engine(username, password, host, port, service_name)
            if engine:
                st.success("Connection successful")
                st.session_state["engine"] = engine
            else:
                st.error("Failed to connect to the database.")

    if "engine" in st.session_state:
        engine = st.session_state["engine"]
        tables, columns = fetch_metadata(engine)

        if tables is not None and columns is not None:
            st.header("Build Your Query")

            selected_tables = st.multiselect("Select Tables", tables["table_name"].tolist())

            query_columns = []
            joins = []
            where_conditions = []

            if selected_tables:
                for table in selected_tables:
                    table_columns = columns[columns["table_name"] == table]["column_name"].tolist()
                    selected_columns = st.multiselect(f"Select Columns for {table}", table_columns)
                    query_columns.extend([f"{table}.{col}" for col in selected_columns])

                if len(selected_tables) > 1:
                    st.subheader("Define Joins")
                    for i in range(len(selected_tables)):
                        for j in range(i + 1, len(selected_tables)):
                            left_table = selected_tables[i]
                            right_table = selected_tables[j]

                            left_columns = columns[columns["table_name"] == left_table]["column_name"].tolist()
                            right_columns = columns[columns["table_name"] == right_table]["column_name"].tolist()

                            st.markdown(f"### Join between {left_table} and {right_table}")
                            left_column = st.selectbox(f"Select column from {left_table}", left_columns, key=f"left_{i}_{j}")
                            right_column = st.selectbox(f"Select column from {right_table}", right_columns, key=f"right_{i}_{j}")

                            if left_column and right_column:
                                join_condition = f"{left_table}.{left_column} = {right_table}.{right_column}"
                                joins.append(join_condition)

                st.subheader("Add WHERE Conditions")
                if query_columns:
                    for col in query_columns:
                        condition = st.text_input(f"Condition for {col} (e.g., = 'value', > 10)", key=f"condition_{col}")
                        if condition:
                            where_conditions.append(f"{col} {condition}")

            if query_columns:
                st.subheader("Query Preview")
                query = f"SELECT {', '.join(query_columns)} FROM {', '.join(selected_tables)}"

                if joins:
                    query += f" WHERE {' AND '.join(joins)}"

                if where_conditions:
                    where_clause = ' AND '.join(where_conditions)
                    if 'WHERE' in query:
                        query += f" AND {where_clause}"
                    else:
                        query += f" WHERE {where_clause}"

                st.text(query)

                if st.button("Execute Query"):
                    try:
                        with engine.connect() as conn:
                            result = pd.read_sql(text(query), conn)
                            st.subheader("Query Results")
                            st.dataframe(result)
                    except Exception as e:
                        st.error(f"Error executing query: {str(e)}")

if __name__ == "__main__":
    main()
