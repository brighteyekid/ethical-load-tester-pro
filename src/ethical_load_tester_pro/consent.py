def get_user_consent() -> bool:
    """
    Obtain explicit user consent for load testing.
    """
    print("\n=== ETHICAL LOAD TESTING CONSENT ===")
    print("Before proceeding, please confirm that:")
    print("1. You have explicit written permission to test the target system")
    print("2. You understand this tool should only be used for authorized testing")
    print("3. You accept responsibility for any consequences of the test")
    
    response = input("\nDo you confirm all of the above? (yes/no): ").lower()
    return response == 'yes' 