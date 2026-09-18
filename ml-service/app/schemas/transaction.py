from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class TransactionFeatures(BaseModel):
    """
    Core features modeled after IEEE-CIS Fraud Detection dataset.
    Includes Transaction table features + Identity table features.
    """
    transaction_ref: Optional[str] = Field(None, description="Unique reference ID from caller")
    transaction_amt: float = Field(..., gt=0, description="Transaction payment amount in USD")
    product_cd: str = Field(..., description="Product code: W, C, R, H, S")
    
    # Card information (card1 - card6)
    card1: Optional[str] = Field(None, description="Payment card number hash/identifier")
    card2: Optional[str] = Field(None, description="Card issuing bank code")
    card3: Optional[str] = Field(None, description="Card issuing country code")
    card4: Optional[str] = Field(None, description="Card network (e.g., visa, mastercard, discover)")
    card5: Optional[str] = Field(None, description="Card category / tier")
    card6: Optional[str] = Field(None, description="Card type (e.g., debit, credit)")
    
    # Address and distance
    addr1: Optional[str] = Field(None, description="Billing zip/region code")
    addr2: Optional[str] = Field(None, description="Billing country code")
    dist1: Optional[float] = Field(None, description="Distance between billing and delivery address")
    dist2: Optional[float] = Field(None, description="Distance from billing address to IP address")
    
    # Email domains
    p_emaildomain: Optional[str] = Field(None, description="Purchaser email domain (e.g., gmail.com, yahoo.com)")
    r_emaildomain: Optional[str] = Field(None, description="Recipient email domain")
    
    # Identity features (Device & Browser)
    device_type: Optional[str] = Field(None, description="Device category: desktop, mobile, tablet")
    device_info: Optional[str] = Field(None, description="Device OS / hardware build string")
    browser_version: Optional[str] = Field(None, description="Browser name and version")
    
    # Additional raw features dict for V-columns, C-columns, D-columns if needed
    additional_features: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Raw C, D, M, V features")

    class Config:
        json_schema_extra = {
            "example": {
                "transaction_ref": "TX-948201",
                "transaction_amt": 389.50,
                "product_cd": "W",
                "card1": "13926",
                "card2": "321",
                "card3": "150",
                "card4": "visa",
                "card5": "226",
                "card6": "credit",
                "addr1": "315",
                "addr2": "87",
                "p_emaildomain": "gmail.com",
                "r_emaildomain": "anonymous-relay.net",
                "device_type": "mobile",
                "device_info": "iOS 17.4",
                "browser_version": "Safari 17.0"
            }
        }
