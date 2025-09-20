import streamlit as st
import pandas as pd
from datetime import datetime
from backend import (
    create_tables, get_all_employees, add_employee,
    create_goal, read_goals, update_goal_status, delete_goal,
    create_task, read_tasks, update_task_approval,
    create_feedback, read_feedback,
    get_performance_history, get_goal_status_counts,
    get_avg_days_to_complete_goal, get_max_min_due_date,
    get_total_tasks_approved
)

# --- Initial Setup and Session State Management ---
if 'init_db' not in st.session_state:
    create_tables()
    st.session_state.init_db = True

if 'user_role' not in st.session_state:
    st.session_state.user_role = 'Manager'

if 'selected_employee' not in st.session_state:
    st.session_state.selected_employee = None

st.set_page_config(layout="wide", page_title="Performance Management System")

st.title("Performance Management System")

# --- Sidebar for Navigation and User Selection ---
with st.sidebar:
    st.header("Navigation")
    st.session_state.user_role = st.radio(
        "Select your role:",
        ('Manager', 'Employee')
    )
    
    st.subheader("Select Employee")
    employees = get_all_employees()
    employee_names = [e[1] for e in employees]
    employee_map = {e[1]: e[0] for e in employees}

    selected_employee_name = st.selectbox(
        "Choose an employee:",
        options=employee_names,
        index=None
    )
    
    if selected_employee_name:
        st.session_state.selected_employee = employee_map[selected_employee_name]
    else:
        st.session_state.selected_employee = None
        
    st.subheader("Add New Employee")
    new_employee_name = st.text_input("New Employee Name:")
    if st.button("Add Employee"):
        if new_employee_name:
            add_employee(new_employee_name)
            st.success(f"Added new employee: {new_employee_name}")
            st.rerun()
        else:
            st.error("Please enter a name for the new employee.")

# --- Main Content Area ---
st.header(f"You are logged in as a: {st.session_state.user_role}")

if st.session_state.selected_employee:
    st.subheader(f"Viewing data for: {selected_employee_name}")

    # --- Goal & Task Setting Section ---
    st.divider()
    st.subheader("Goal & Task Management")

    if st.session_state.user_role == 'Manager':
        # Manager can set goals
        with st.expander("Set a New Goal"):
            with st.form("goal_form"):
                goal_description = st.text_area("Goal Description:")
                due_date = st.date_input("Due Date:", min_value=datetime.today())
                submit_goal = st.form_submit_button("Set Goal")
                
                if submit_goal:
                    if st.session_state.selected_employee and goal_description:
                        create_goal(st.session_state.selected_employee, goal_description, due_date)
                        st.success("Goal set successfully!")
                        st.rerun()
                    else:
                        st.error("Please select an employee and provide a description.")
        
        st.subheader("Current Goals")
        goals_data = read_goals(st.session_state.selected_employee)
        if goals_data:
            df_goals = pd.DataFrame(goals_data, columns=['ID', 'Employee', 'Description', 'Due Date', 'Status'])
            st.dataframe(df_goals, use_container_width=True)

            # Manager can update goal status
            with st.form("goal_status_form"):
                goal_id_to_update = st.selectbox(
                    "Select Goal ID to Update Status:",
                    options=df_goals['ID'].tolist(),
                    index=None
                )
                new_status = st.radio(
                    "New Status:",
                    ('Draft', 'In Progress', 'Completed', 'Cancelled')
                )
                submit_status = st.form_submit_button("Update Goal Status")
                
                if submit_status and goal_id_to_update:
                    update_goal_status(goal_id_to_update, new_status)
                    st.success(f"Status for Goal {goal_id_to_update} updated to '{new_status}'")
                    
                    # --- Automated Feedback Trigger ---
                    if new_status == 'Completed':
                        trigger_feedback_text = "Congratulations on completing this goal! Your hard work is appreciated."
                        create_feedback(goal_id_to_update, st.session_state.selected_employee, trigger_feedback_text)
                        st.info("Automated 'Completed' feedback has been generated.")
                    st.rerun()

    elif st.session_state.user_role == 'Employee':
        # Employee can log tasks for their goals
        st.subheader("My Goals")
        my_goals = read_goals(st.session_state.selected_employee)
        if my_goals:
            df_my_goals = pd.DataFrame(my_goals, columns=['ID', 'Employee', 'Description', 'Due Date', 'Status'])
            st.dataframe(df_my_goals, use_container_width=True)
            
            with st.expander("Log a New Task for a Goal"):
                with st.form("task_form"):
                    goal_id_for_task = st.selectbox(
                        "Select a Goal to Log a Task for:",
                        options=df_my_goals['ID'].tolist(),
                        format_func=lambda x: f"Goal {x}: {df_my_goals.loc[df_my_goals['ID'] == x, 'Description'].iloc[0][:50]}...",
                        index=None
                    )
                    task_description = st.text_area("Task Description:")
                    submit_task = st.form_submit_button("Log Task")
                    
                    if submit_task and goal_id_for_task and task_description:
                        create_task(goal_id_for_task, st.session_state.selected_employee, task_description)
                        st.success("Task logged for manager approval!")
                        st.rerun()
                    else:
                        st.error("Please select a goal and provide a task description.")
        else:
            st.info("You have no goals assigned yet.")

    # --- Task Approval Section (Manager View) ---
    if st.session_state.user_role == 'Manager':
        st.divider()
        st.subheader("Tasks Awaiting Approval")
        all_tasks = read_tasks(employee_id=st.session_state.selected_employee)
        if all_tasks:
            df_tasks = pd.DataFrame(all_tasks, columns=['Task ID', 'Goal Description', 'Task Description', 'Approved'])
            st.dataframe(df_tasks, use_container_width=True)
            
            with st.form("task_approval_form"):
                task_id_to_approve = st.selectbox(
                    "Select Task ID to Approve:",
                    options=df_tasks['Task ID'].tolist(),
                    index=None
                )
                submit_approval = st.form_submit_button("Approve Task")
                
                if submit_approval and task_id_to_approve:
                    update_task_approval(task_id_to_approve, True)
                    st.success(f"Task {task_id_to_approve} has been approved.")
                    st.rerun()
        else:
            st.info("No tasks to approve.")
    
    # --- Feedback Section ---
    st.divider()
    st.subheader("Feedback")
    
    if st.session_state.user_role == 'Manager':
        with st.expander("Provide Feedback"):
            goals_for_feedback = read_goals(st.session_state.selected_employee)
            if goals_for_feedback:
                df_goals_feedback = pd.DataFrame(goals_for_feedback, columns=['ID', 'Employee', 'Description', 'Due Date', 'Status'])
                with st.form("feedback_form"):
                    goal_id_for_feedback = st.selectbox(
                        "Select a Goal to provide feedback on:",
                        options=df_goals_feedback['ID'].tolist(),
                        format_func=lambda x: f"Goal {x}: {df_goals_feedback.loc[df_goals_feedback['ID'] == x, 'Description'].iloc[0][:50]}...",
                        index=None
                    )
                    feedback_text = st.text_area("Feedback:")
                    submit_feedback = st.form_submit_button("Submit Feedback")
                    
                    if submit_feedback and goal_id_for_feedback and feedback_text:
                        create_feedback(goal_id_for_feedback, st.session_state.selected_employee, feedback_text)
                        st.success("Feedback submitted successfully!")
                        st.rerun()
            else:
                st.info("No goals to provide feedback on.")

    elif st.session_state.user_role == 'Employee':
        st.subheader("My Feedback History")
        # Fetch goals for this employee and then their feedback
        goals_data_for_feedback = read_goals(st.session_state.selected_employee)
        if goals_data_for_feedback:
            for goal_id, _, description, _, _ in goals_data_for_feedback:
                feedback_list = read_feedback(goal_id)
                if feedback_list:
                    st.markdown(f"**Feedback for Goal {goal_id}:** {description}")
                    for _, text, created_at in feedback_list:
                        st.markdown(f"> **{created_at.strftime('%Y-%m-%d')}**: {text}")
        else:
            st.info("No feedback available yet.")
            
    # --- Reporting Section ---
    st.divider()
    st.subheader("Performance History Report")
    history_data = get_performance_history(st.session_state.selected_employee)
    if history_data:
        for goal in history_data:
            st.markdown(f"**Goal ID:** {goal['goal_id']}")
            st.markdown(f"**Description:** {goal['description']}")
            st.markdown(f"**Due Date:** {goal['due_date']}")
            st.markdown(f"**Status:** {goal['status']}")
            st.markdown(f"**Date Created:** {goal['created_at']}")
            if goal['feedbacks']:
                st.markdown("**Associated Feedback:**")
                for feedback_text, created_at in goal['feedbacks']:
                    st.markdown(f"- {feedback_text} (on {created_at.strftime('%Y-%m-%d')})")
            st.markdown("---")
    else:
        st.info("No performance history to display.")

    # --- Business Insights Section ---
    st.divider()
    st.subheader("Business Insights")
    st.write("Leveraging core database functions to provide actionable insights.")

    # Goal Status Count (COUNT)
    goal_counts = get_goal_status_counts(st.session_state.selected_employee)
    if goal_counts:
        st.metric("Total Goals", sum(goal_counts.values()))
        df_counts = pd.DataFrame(list(goal_counts.items()), columns=['Status', 'Count'])
        st.bar_chart(df_counts.set_index('Status'))

    col1, col2 = st.columns(2)
    
    with col1:
        # Average Completion Time (AVG)
        avg_days = get_avg_days_to_complete_goal(st.session_state.selected_employee)
        if avg_days is not None:
            st.metric("Avg Days to Complete Goal", f"{avg_days:.2f} days")
        else:
            st.metric("Avg Days to Complete Goal", "N/A")

        # Total Approved Tasks (SUM/COUNT)
        total_approved_tasks = get_total_tasks_approved()
        st.metric("Total Approved Tasks", total_approved_tasks)

    with col2:
        # Min and Max Due Dates (MIN, MAX)
        min_date, max_date = get_max_min_due_date()
        if min_date and max_date:
            st.markdown(f"**Earliest Due Date:** {min_date}")
            st.markdown(f"**Latest Due Date:** {max_date}")

else:
    st.warning("Please select an employee from the sidebar to view their information.")
