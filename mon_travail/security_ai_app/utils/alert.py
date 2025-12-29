def risk_decision(anomaly_score, detected_objects):
    TH_ANOMALY = 0.002
    DANGEROUS = ["Knife", "Pistol", "Gun-Rifle-", "Grenade"]

    weapon_found = any(obj in DANGEROUS for obj in detected_objects)

    if anomaly_score > TH_ANOMALY and weapon_found:
        return "MENACE CRITIQUE", "🔴"
    elif weapon_found:
        return "OBJET DANGEREUX", "🟠"
    elif anomaly_score > TH_ANOMALY:
        return "ANOMALIE COMPORTEMENTALE", "🟡"
    else:
        return "SITUATION NORMALE", "🟢"
