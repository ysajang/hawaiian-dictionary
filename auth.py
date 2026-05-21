"""
Simple password authentication for the dictionary app.
Uses config sheet password value for access control.
"""

import streamlit as st


def check_auth(correct_password: str) -> bool:
    """Display login form and validate password.

    Manages authentication state via st.session_state.
    Once authenticated, the login form is no longer shown.
    If no password is configured, auto-authenticates.
    """
    if st.session_state.get("authenticated"):
        return True

    # No password set — skip auth
    if not correct_password:
        st.session_state["authenticated"] = True
        return True

    st.markdown(
        """
        <div style="text-align:center; padding:3rem 0 1rem 0;">
            <h1 style="font-family:'Playfair Display',Georgia,serif;
                        font-size:3.5rem; font-weight:700;
                        color:#2D2D2D; margin-bottom:0.2rem;">
                Olii
            </h1>
            <p style="font-family:sans-serif; font-size:0.85rem;
                       letter-spacing:0.25em; color:#5B7B71;
                       text-transform:uppercase; margin-top:0;">
                Hawaiian Context Dictionary
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("login_form"):
        password_input = st.text_input(
            "Password",
            type="password",
            placeholder="Enter password",
        )
        submitted = st.form_submit_button(
            "Enter",
            use_container_width=True,
            type="primary",
        )

        if submitted:
            if password_input == correct_password:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Incorrect password. Please try again.")

    return False
