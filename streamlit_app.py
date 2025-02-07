import nibabel as nib
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
import tempfile
from PIL import Image

# Définition des constantes
file_names = ["skeletal_muscle.nii.gz", "subcutaneous_fat.nii.gz", "torso_fat.nii.gz"]
masse_vol_graisse = 0.9196
masse_vol_muscle = 1.06

# Chargement de l'icône
icon_path = "./icon.png"
icon = Image.open(icon_path)

# Interface Streamlit
# Interface Streamlit avec barre latérale
st.set_page_config(page_title="Analyse de Segmentation IRM", page_icon=icon, layout="centered")

# Affichage dans la barre latérale
st.sidebar.image(icon, width=100)
st.sidebar.title("Analyse de segmentation IRM corps entier")
st.sidebar.subheader("Développé par Dr Florentin Kucharczak")

st.sidebar.write("""
    Ce programme permet d'analyser la composition corporelle graisseuse et musculaire à partir des fichiers NIfTI 
    (.nii.gz) issus d'une segmentation d'IRM corps entier. Il calcule le volume musculaire, de graisse (sous-cutanée et viscérale),
    ainsi que les masses correspondantes et les rapports muscle/graisse et graisse viscérale/sous-cutanée. \\
    Les résultats sont ensuite affichés et téléchargeables en sous forme de fichier Excel.
""")

# Affichage principal
st.subheader("Chargement des fichiers NIfTI") 


def analyze_voxel_data(uploaded_files):
    voxel_data = {}
    voxel_volume = None
    
    for uploaded_file in uploaded_files:
        file_name = uploaded_file.name
        if file_name in file_names:
            # Sauvegarde temporaire du fichier
            with tempfile.NamedTemporaryFile(delete=False, suffix=".nii.gz") as tmpfile:
                tmpfile.write(uploaded_file.read())
                tmpfile_path = tmpfile.name
            
            img = nib.load(tmpfile_path)
            data = img.get_fdata()
            voxel_count = (data > 0).sum()
            voxel_volume = abs(img.header.get_zooms()[0] * img.header.get_zooms()[1] * img.header.get_zooms()[2]) / 1000
            voxel_data[file_name] = voxel_count
    
    vox_count_muscle = voxel_data.get("skeletal_muscle.nii.gz", 0)
    vox_count_graisse_viscerale = voxel_data.get("torso_fat.nii.gz", 0)
    vox_count_graisse_sous_cut = voxel_data.get("subcutaneous_fat.nii.gz", 0)
    
    volume_muscle = vox_count_muscle * voxel_volume if vox_count_muscle else None
    volume_graisse_viscerale = vox_count_graisse_viscerale * voxel_volume if vox_count_graisse_viscerale else None
    volume_graisse_sous_cut = vox_count_graisse_sous_cut * voxel_volume if vox_count_graisse_sous_cut else None
    
    # Création d'une liste de valeurs à afficher dans une colonne
    result = [
        ("Volume Muscle (cm³)", volume_muscle),
        ("Volume Graisse Sous-cutanée (cm³)", volume_graisse_sous_cut),
        ("Volume Graisse Viscerale (cm³)", volume_graisse_viscerale),
        ("Masse Muscle (kg)", volume_muscle * masse_vol_muscle / 1000 if volume_muscle else None),
        ("Masse Graisse Sous-cutanée (kg)", volume_graisse_sous_cut * masse_vol_graisse / 1000 if volume_graisse_sous_cut else None),
        ("Masse Graisse Viscerale (kg)", volume_graisse_viscerale * masse_vol_graisse / 1000 if volume_graisse_viscerale else None),
        ("Rapport Graisse Sous-cutanée / Viscerale", (volume_graisse_sous_cut * masse_vol_graisse / 1000 if volume_graisse_sous_cut else None) /
                                                     (volume_graisse_viscerale * masse_vol_graisse / 1000 if volume_graisse_viscerale else None)),
        ("Rapport Graisse / Muscle", ((volume_graisse_sous_cut * masse_vol_graisse / 1000 if volume_graisse_sous_cut else None) +
                                      (volume_graisse_viscerale * masse_vol_graisse / 1000 if volume_graisse_viscerale else None)) /
                                      (volume_muscle * masse_vol_muscle / 1000 if volume_muscle else None))
    ]
    
    # Conversion en DataFrame avec une seule colonne pour les résultats
    df = pd.DataFrame(result, columns=["Métrique", "Valeur"])
    
    return df


def convert_df_to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

def plot_data(df):
    # Sélectionner les valeurs des masses pour les trois tissus
    masses = [
        df['Valeur'].iloc[3],  # Masse Muscle (kg)
        df['Valeur'].iloc[4],  # Masse Graisse Sous-cutanée (kg)
        df['Valeur'].iloc[5]   # Masse Graisse Viscerale (kg)
    ]
    tissues = ['Muscle', 'Graisse Sous-cutanée', 'Graisse Viscerale']
    
    # Création d'une figure pour l'histogramme
    fig, ax = plt.subplots(figsize=(8, 5))
    colors = ["#ff7f0e", "#2ca02c", "#ff6347"]
    
    # Création de l'histogramme avec les masses des trois tissus
    sns.barplot(x=tissues, y=masses, palette=colors, ax=ax)

    # Affichage des valeurs au sommet des barres
    for i, value in enumerate(masses):
        ax.text(i, value + 0.05, f'{value:.2f} kg', ha='center', va='bottom')

    ax.set_ylabel("Masse (kg)")
    ax.set_title("Masse des différents tissus")

    # Affichage du graphique
    st.pyplot(fig)



uploaded_files = st.file_uploader("Déposez les 3 fichiers NIfTI : skeletal_muscle.nii.gz, subcutaneous_fat.nii.gz et torso_fat.nii.gz", type=["nii.gz"], accept_multiple_files=True)

if uploaded_files:
    uploaded_filenames = [file.name for file in uploaded_files]
    missing_files = [f for f in file_names if f not in uploaded_filenames]
    extra_files = [f for f in uploaded_filenames if f not in file_names]
    
    if missing_files or extra_files:
        st.error(f"Les fichiers uploadés ne correspondent pas aux fichiers attendus.\n\nManquants: {missing_files}\n\nSupplémentaires: {extra_files}")
    elif len(uploaded_files) == 3:
        df_result = analyze_voxel_data(uploaded_files)
        st.write("### Résultats :")
        st.dataframe(df_result)  # Affichage sous forme de tableau vertical
        
        plot_data(df_result)
        
        excel_data = convert_df_to_excel(df_result)
        # Ajout d'une entrée de texte pour l'ID anonymisé du patient
        patient_id = st.text_input("Id. anonymisé du patient", value="p_xxx")
        st.download_button(label="Télécharger les résultats en Excel", data=excel_data, file_name=f"{patient_id}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        st.warning("Veuillez uploader exactement 3 fichiers NIfTI (.nii.gz)")

