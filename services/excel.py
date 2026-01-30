import pandas as pd
import io
from typing import List
from database.models import User

def export_users_to_excel(users: List[User]) -> io.BytesIO:
    data = []
    for user in users:
        data.append({
            "ID": user.id,
            "Telegram ID": user.telegram_id,
            "Full Name": user.full_name,
            "Username": user.username,
            "Is Admin": user.is_admin
        })
    
    df = pd.DataFrame(data)
    output = io.BytesIO()
    
    # Write to Excel
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Users')
    
    output.seek(0)
    return output
