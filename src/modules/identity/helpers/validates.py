from pathlib import Path
from typing import Dict


class PathValidator:

    @staticmethod
    def validate_and_check_next_directory(path: str) -> Dict[str, any]:
        """
        Validates a path and checks if the specified next directory exists.

        Args:
            path: Path to be validated (e.g., 'src/modules/ai/engines/lchain/feature')

        Returns:
            dict with information about validation and verification
        """

        # Expected directory (hardcoded)
        NEXT_DIRECTORY = "finance"

        result = {
            "original_path": path,
            "valid_path": False,
            "path_exists": False,
            "next_directory_exists": False,
            "full_path": None,
            "feature": "",
            "message": "",
        }

        # Path validation
        if not path or not isinstance(path, str):
            result["message"] = "Invalid path: must be a non-empty string"
            return result

        # Remove extra spaces and slashes
        path = path.strip().rstrip("/\\")

        if not path:
            result["message"] = "Invalid path: empty string after normalization"
            return result

        # Validation of dangerous characters
        invalid_characters = ["..", "\0"]
        if any(char in path for char in invalid_characters):
            result["message"] = "Path contains invalid or dangerous characters"
            return result

        result["valid_path"] = True

        try:
            # Convert to Path object
            path_obj = Path(path)

            # Check if the path exists
            if path_obj.exists():
                result["path_exists"] = True

                # Check if it's a directory
                if not path_obj.is_dir():
                    result["message"] = "The path exists but is not a directory"
                    return result
            else:
                result["message"] = "The path does not exist in the file system"
                return result

            # Check if the next directory exists
            next_path = path_obj / NEXT_DIRECTORY
            result["full_path"] = str(next_path)

            if next_path.exists() and next_path.is_dir():
                result["next_directory_exists"] = True
                result["message"] = (
                    f"Success! The '{NEXT_DIRECTORY}' directory exists in {path}"
                )
                result["feature"] = NEXT_DIRECTORY
            else:
                result["message"] = (
                    f"The '{NEXT_DIRECTORY}' directory was not found in {path}"
                )

        except Exception as e:
            result["message"] = f"Error processing path: {str(e)}"

        return result


# Usage example
if __name__ == "__main__":
    # Test 1
    result = PathValidator.validate_and_check_next_directory(
        "src/modules/ai/engines/lchain/feature"
    )
    print(f"Path: {result['original_path']}")
    print(f"Valid: {result['valid_path']}")
    print(f"Exists: {result['path_exists']}")
    print(f"Next directory exists: {result['next_directory_exists']}")
    print(f"Message: {result['message']}")
    print(f"Full path: {result['full_path']}")
    print("-" * 50)

    # Test 2 - Invalid path
    result2 = PathValidator.validate_and_check_next_directory("")
    print(f"Message: {result2['message']}")
