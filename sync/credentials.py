from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class FacebookAdsCredentials(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    ad_account_id: str = Field(..., alias="adAccountId")
    access_token: str = Field(..., alias="accessToken")
    app_id: str = Field(..., alias="appId")
    app_secret: str = Field(..., alias="appSecret")
    long_lived_token: Optional[str] = Field(None, alias="longLivedToken")
    auth_method: Optional[str] = Field(None, alias="authMethod")
    account_status: Optional[str] = Field(None, alias="accountStatus")
    business_id: Optional[str] = Field(None, alias="businessId")
