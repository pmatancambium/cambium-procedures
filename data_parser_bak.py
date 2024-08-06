import re
import json
import chardet
from abc import ABC, abstractmethod

class Parser(ABC):
    @abstractmethod
    def parse(self, data: str) -> list:
        pass

class ServiceCallParser(Parser):
    def parse(self, data: str) -> list:
        return self.parse_service_calls(data)

    def parse_service_calls(self, text: str) -> list:
        # Split the text into individual service calls
        service_calls = re.split(r'(\d{9})\n', text)
        
        # Remove the first empty entry (if any)
        if service_calls[0] == '':
            service_calls.pop(0)
        
        # Create a list of service call dictionaries
        parsed_service_calls = []
        
        # Iterate over the service calls in pairs of (id, details)
        for i in range(0, len(service_calls), 2):
            service_call_id = service_calls[i]
            service_call_details = service_calls[i + 1]
            
            # Split the details into individual lines
            lines = service_call_details.strip().split('\n')
            
            # Create a dictionary to store the parsed details
            service_call_dict = {
                "ServiceCallID": service_call_id,
                "Interactions": []
            }
            
            # Variables to keep track of the current interaction
            current_interaction = None
            
            # Iterate over the lines to extract information
            for line in lines:
                if re.match(r'\d\s*={10,}', line):  # Separator line
                    continue
                elif re.match(r'\d\s*_{10,}', line):  # Separator line
                    continue
                elif 'Added by' in line or 'תאריך' in line:
                    # Save the current interaction if it exists
                    if current_interaction:
                        service_call_dict["Interactions"].append(current_interaction)
                    
                    # Start a new interaction
                    current_interaction = {
                        "AddedBy": None,
                        "Timestamp": None,
                        "Message": ""
                    }
                    
                    # Extract added by and timestamp
                    if 'Added by' in line:
                        parts = line.split('Added by')
                        current_interaction["AddedBy"] = parts[1].split('on')[0].strip()
                        if 'on' in parts[1]:
                            current_interaction["Timestamp"] = parts[1].split('on')[1].strip(' :')
                    else:
                        parts = line.split(':')
                        if len(parts) > 1:
                            current_interaction["Timestamp"] = parts[1].strip()
                else:
                    if current_interaction:
                        current_interaction["Message"] += line[1:].strip() + "\n"
            
            # Add the last interaction
            if current_interaction:
                service_call_dict["Interactions"].append(current_interaction)
            
            # Append the service call dict to the list
            parsed_service_calls.append(service_call_dict)
        
        return parsed_service_calls