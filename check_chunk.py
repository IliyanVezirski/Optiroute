try:
    from config import OSRMConfig
    osrm = OSRMConfig()
    
    with open("chunk_result.txt", "w") as f:
        f.write(f"chunk_size = {osrm.chunk_size}\n")
        f.write("Success!\n")
    print("Result written to chunk_result.txt")
    
except Exception as e:
    with open("chunk_error.txt", "w") as f:
        f.write(f"Error: {e}\n")
        import traceback
        f.write(traceback.format_exc())
    print("Error written to chunk_error.txt") 