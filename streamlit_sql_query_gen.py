import streamlit as st
import cx_Oracle
import pandas as pd

class OracleSQLQueryBuilder:
    def __init__(self):
        # Database connection parameters
        self.connection = None
        self.tables = []
        self.columns = {}

    def connect_to_database(self, username, password, dsn):
        """
        Establish connection to Oracle database
        """
        try:
            self.connection = cx_Oracle.connect(
                user=username,
                password=password,
                dsn=dsn
            )
            
            # Fetch all tables
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT table_name 
                FROM user_tables
            """)
            self.tables = [table[0] for table in cursor.fetchall()]
            
            # Fetch columns for each table
            for table in self.tables:
                cursor.execute(f"""
                    SELECT column_name, data_type 
                    FROM user_tab_columns 
                    WHERE table_name = '{table}'
                """)
                self.columns[table] = cursor.fetchall()
            
            cursor.close()
            return True
        except cx_Oracle.Error as error:
            st.error(f"Error connecting to database: {error}")
            return False

    def build_query_ui(self):
        """
        Build the query construction UI with multi-column join support
        """
        st.header("Oracle SQL Query Builder")
        
        # Table selection
        st.subheader("1. Select Tables")
        selected_tables = st.multiselect("Choose tables", self.tables)
        
        # Columns selection
        st.subheader("2. Select Columns")
        selected_columns = {}
        for table in selected_tables:
            columns = [col[0] for col in self.columns[table]]
            selected_columns[table] = st.multiselect(
                f"Columns for {table}", 
                columns, 
                default=columns
            )
        
        # Multi-column Join conditions
        st.subheader("3. Join Conditions")
        join_type = st.selectbox("Join Type", [
            "INNER JOIN", 
            "LEFT OUTER JOIN", 
            "RIGHT OUTER JOIN", 
            "FULL OUTER JOIN"
        ])
        
        # Dynamic join condition builder
        join_conditions = []
        if len(selected_tables) > 1:
            st.info("Define join conditions between tables. Use the format: table1.column = table2.column")
            
            for i in range(len(selected_tables) - 1):
                st.markdown(f"**Join Conditions between {selected_tables[i]} and {selected_tables[i+1]}**")
                
                # Number of join conditions
                num_join_conditions = st.number_input(
                    f"Number of join conditions for {selected_tables[i]} and {selected_tables[i+1]}", 
                    min_value=1, 
                    max_value=5, 
                    value=1
                )
                
                table1_cols = [col[0] for col in self.columns[selected_tables[i]]]
                table2_cols = [col[0] for col in self.columns[selected_tables[i+1]]]
                
                table_join_conditions = []
                for j in range(num_join_conditions):
                    col1 = st.selectbox(
                        f"Column from {selected_tables[i]}", 
                        table1_cols, 
                        key=f"join_col1_{i}_{j}"
                    )
                    col2 = st.selectbox(
                        f"Column from {selected_tables[i+1]}", 
                        table2_cols, 
                        key=f"join_col2_{i}_{j}"
                    )
                    
                    # Construct join condition
                    join_condition = f"{selected_tables[i]}.{col1} = {selected_tables[i+1]}.{col2}"
                    table_join_conditions.append(join_condition)
                
                # Combine multiple join conditions with AND
                combined_join_condition = " AND ".join(table_join_conditions)
                join_conditions.append(combined_join_condition)
        
        # Filtering
        st.subheader("4. Filtering")
        where_conditions = st.text_area("WHERE Conditions", 
                                        placeholder="e.g., column1 > 100 AND column2 = 'value'")
        
        # Aggregation
        st.subheader("5. Aggregation")
        aggregation = st.selectbox("Aggregation Function", [
            "None", "COUNT", "SUM", "AVG", "MAX", "MIN"
        ])
        agg_column = None
        if aggregation != "None":
            agg_tables = list(selected_columns.keys())
            agg_table = st.selectbox("Table for Aggregation", agg_tables)
            agg_column = st.selectbox(
                "Column for Aggregation", 
                [col for col in selected_columns[agg_table]]
            )
        
        # Generate Query Button
        if st.button("Generate Query"):
            query = self.generate_query(
                selected_tables, 
                selected_columns, 
                join_type, 
                join_conditions, 
                where_conditions,
                aggregation,
                agg_table,
                agg_column
            )
            st.code(query)
            
            # Optional: Execute Query
            if st.button("Execute Query"):
                self.execute_query(query)

    def generate_query(self, tables, selected_columns, join_type, 
                       join_conditions, where_conditions, 
                       aggregation, agg_table, agg_column):
        """
        Generate SQL query based on user selections with multi-column join support
        """
        # Select columns
        select_clause = []
        for table, cols in selected_columns.items():
            select_clause.extend([f"{table}.{col}" for col in cols])
        
        # Aggregation handling
        if aggregation != "None" and agg_table and agg_column:
            select_clause = [f"{aggregation}({agg_table}.{agg_column}) as {aggregation.lower()}_{agg_column}"]
        
        # From and Join clause with multi-column support
        from_clause = f"FROM {tables[0]}"
        for i in range(1, len(tables)):
            from_clause += f" {join_type} {tables[i]} ON ({join_conditions[i-1]})"
        
        # Where clause
        where_clause = f"WHERE {where_conditions}" if where_conditions else ""
        
        # Construct full query
        query = f"SELECT {', '.join(select_clause)} {from_clause} {where_clause}"
        return query

    def execute_query(self, query):
        """
        Execute the generated query
        """
        try:
            df = pd.read_sql(query, self.connection)
            st.dataframe(df)
        except Exception as e:
            st.error(f"Error executing query: {e}")

def main():
    st.title("Oracle SQL Query Builder")
    
    # Connection Parameters
    with st.sidebar:
        st.header("Database Connection")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        dsn = st.text_input("DSN (Data Source Name)")
        
        if st.button("Connect"):
            query_builder = OracleSQLQueryBuilder()
            if query_builder.connect_to_database(username, password, dsn):
                st.success("Connected Successfully!")
                query_builder.build_query_ui()

if __name__ == "__main__":
    main()
