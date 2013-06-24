#ifndef TESUNCERTAINTY_CXX
#define TESUNCERTAINTY_CXX
#include "assert.h"
#include "TauCorrUncert/TESUncertainty.h"

using namespace std;
using namespace TauCorrUncert;

ClassImp(TESUncertainty)

static	const unsigned int n_EtaBins = 5;
double EtaBins[n_EtaBins + 1] = {
  0.,0.3,0.8,1.3,1.6,2.5
};
TString PF_EtaBins[n_EtaBins] = {
  "0_03","03_08","08_13","13_16","16_25"
};
//TODO: get rid of this array and use a proper object as it should be in C++
TH1D* h1_TES_comps[21][2][5];

TESUncertainty::~TESUncertainty()
{
  map<TString, TH1D*>::iterator it;
  for (it = map_histo.begin(); it != map_histo.end(); ++it)
    if((*it).second)
      delete (*it).second;
}

TESUncertainty::TESUncertainty(TString datafile) :
  GeV(1000.),
  m_dInSituStat1P(0.013),
  m_dInSituStat3P(0.014),
  m_dInSituSyst1P(0.006),
  m_dInSituSyst3P(0.007)
{
  TFile* file = TFile::Open(datafile);
  if(!file || !file->IsOpen())
    {
      Fatal("", "Could not open %s", datafile.Data());
      return;
    }

  m_nEta = 5;

  map_components[FINAL] = "TESUFinal_";
  map_components[SINGLEPARTICLE] = "TESUsinglep_";

  map_components[EOP_RSP] = "TESUEoP_Rsp_";
  map_components[EOP_SYST] = "TESUEoP_syst_";
  map_components[CTB_RSP] = "TESUCTB_Rsp_";
  map_components[CTB_SYST] = "TESUCTB_syst_";
  map_components[EM] = "TESUEM_";
  map_components[LCW] = "TESUShowerShape_";
  map_components[Bias] = "TESUBias_";

  map_components[UE] = "TESUue_";
  map_components[DM] = "TESUdm_";
  map_components[CLOSURE] = "TESUclosure_";
  map_components[PU] = "TESUpu_";
  map_components[SHOWERMODEL] = "TESUshowerm_";
  map_components[REMAININGSYS] = "TESRemainingSys_";
  for(int ieta = 0; ieta < m_nEta; ++ieta)
    {
      for(int itrack = 0; itrack < 2; ++itrack)
        {
	  TString prongPF = "_1p";
	  if(itrack == 1)
	    prongPF = "_3p";

	  h1_TES_comps[FINAL][itrack][ieta] = GetHist(file, map_components[FINAL]+PF_EtaBins[ieta]+prongPF);
	  h1_TES_comps[SINGLEPARTICLE][itrack][ieta] = GetHist(file, map_components[SINGLEPARTICLE]+PF_EtaBins[ieta]+prongPF);
	  h1_TES_comps[UE][itrack][ieta] = GetHist(file, map_components[UE]+PF_EtaBins[ieta]+prongPF);
	  h1_TES_comps[DM][itrack][ieta] = GetHist(file, map_components[DM]+PF_EtaBins[ieta]+prongPF);
	  h1_TES_comps[CLOSURE][itrack][ieta] = GetHist(file, map_components[CLOSURE]+PF_EtaBins[ieta]+prongPF);
	  h1_TES_comps[PU][itrack][ieta] = GetHist(file, map_components[PU]+PF_EtaBins[ieta]+prongPF);

	  if(ieta > 1)
	    h1_TES_comps[SHOWERMODEL][itrack][ieta] = GetHist(file, map_components[SHOWERMODEL]+PF_EtaBins[ieta]+prongPF);
	  else
            {
	      h1_TES_comps[SHOWERMODEL][itrack][ieta] = GetHist(file, map_components[FINAL]+PF_EtaBins[ieta]+prongPF);
	      h1_TES_comps[SHOWERMODEL][itrack][ieta]->Reset("ICESM");
            }

	  h1_TES_comps[OTHERS][itrack][ieta] = GetHist(file, map_components[UE]+PF_EtaBins[ieta]+prongPF);
	  for(int ibin = 1; ibin < h1_TES_comps[OTHERS][itrack][ieta]->GetNbinsX() + 1; ++ibin)
            {
	      double bincontentue=  h1_TES_comps[OTHERS][itrack][ieta]->GetBinContent(ibin);
	      double bincontentdm=  h1_TES_comps[DM][itrack][ieta]->GetBinContent(ibin);
	      double bincontentclosure=  h1_TES_comps[CLOSURE][itrack][ieta]->GetBinContent(ibin);
	      double bincontentshower=  h1_TES_comps[SHOWERMODEL][itrack][ieta]->GetBinContent(ibin);
	      h1_TES_comps[OTHERS][itrack][ieta]->SetBinContent(ibin,
								sqrt(bincontentue * bincontentue +
								     bincontentdm * bincontentdm +
								     bincontentclosure * bincontentclosure +
								     bincontentshower * bincontentshower));
            }
	  // total - closure - pu
	  h1_TES_comps[REMAININGSYS][itrack][ieta] = GetHist(file, map_components[FINAL]+PF_EtaBins[ieta]+prongPF);
	  
	  for(int ibin = 1; ibin < h1_TES_comps[OTHERS][itrack][ieta]->GetNbinsX() + 1; ++ibin)
            {
	      double bincontentfinal =  pow(h1_TES_comps[FINAL][itrack][ieta]->GetBinContent(ibin), 2);
	      double bincontentpu =  pow(h1_TES_comps[PU][itrack][ieta]->GetBinContent(ibin), 2);
	      double bincontentclosure =  pow(h1_TES_comps[CLOSURE][itrack][ieta]->GetBinContent(ibin), 2);
	      h1_TES_comps[REMAININGSYS][itrack][ieta]->SetBinContent(ibin,
								      sqrt(bincontentfinal -
									   bincontentclosure -
									   bincontentpu));

            }

            h1_TES_comps[EOP_RSP][itrack][ieta] = GetHist(file, map_components[EOP_RSP]+PF_EtaBins[ieta]+prongPF);
            h1_TES_comps[EOP_SYST][itrack][ieta] = GetHist(file, map_components[EOP_SYST]+PF_EtaBins[ieta]+prongPF);
            h1_TES_comps[CTB_RSP][itrack][ieta] = GetHist(file, map_components[CTB_RSP]+PF_EtaBins[ieta]+prongPF);
            h1_TES_comps[CTB_SYST][itrack][ieta] = GetHist(file, map_components[CTB_SYST]+PF_EtaBins[ieta]+prongPF);
            h1_TES_comps[EM][itrack][ieta] = GetHist(file, map_components[EM]+PF_EtaBins[ieta]+prongPF);
            h1_TES_comps[LCW][itrack][ieta] = GetHist(file, map_components[LCW]+PF_EtaBins[ieta]+prongPF);
            h1_TES_comps[Bias][itrack][ieta] = GetHist(file, map_components[Bias]+PF_EtaBins[ieta]+prongPF);

            h1_TES_comps[EOP][itrack][ieta] = GetHist(file, map_components[EOP_RSP]+PF_EtaBins[ieta]+prongPF);
            for(int ibin = 1; ibin < h1_TES_comps[EOP][itrack][ieta]->GetNbinsX() + 1; ++ibin)
            {
                double bincontent = h1_TES_comps[EOP][itrack][ieta]->GetBinContent(ibin);
                double bincontent2 = h1_TES_comps[EOP_SYST][itrack][ieta]->GetBinContent(ibin);
                h1_TES_comps[EOP][itrack][ieta]->SetBinContent(ibin, sqrt(bincontent*bincontent + bincontent2*bincontent2) );
            }

            h1_TES_comps[CTB][itrack][ieta] = GetHist(file, map_components[CTB_RSP]+PF_EtaBins[ieta]+prongPF);
            for(int ibin = 1; ibin < h1_TES_comps[CTB][itrack][ieta]->GetNbinsX() + 1; ++ibin)
            {
                double bincontent = h1_TES_comps[CTB][itrack][ieta]->GetBinContent(ibin);
                double bincontent2 = h1_TES_comps[CTB_SYST][itrack][ieta]->GetBinContent(ibin);
                h1_TES_comps[CTB][itrack][ieta]->SetBinContent(ibin, sqrt(bincontent*bincontent + bincontent2*bincontent2) );
            }

        }
    }

  Info("", "data loaded from %s", datafile.Data());
  file->Close();
  delete file;
}

TH1D* TESUncertainty::GetHist(TFile* file, TString name)
{
  TH1D* hist = (TH1D*)file->Get(name);
  if (!hist)
    {
      Fatal("GetHist", "Could not get required histogram %s", name.Data());
      return 0;
    }
  hist = (TH1D*)hist->Clone();
  hist->SetDirectory(0);
  return hist;
}

double TESUncertainty::GetTESShift(double pt, // MeV
				   int ntracks)
{
 pt = pt / GeV;
 if(pt > 70.)
   return 0.;
 double alpha = ntracks == 1 ? 0.008 : 0.011;
 alpha = interpolateLin(pt, alpha);
 return alpha / (1. - alpha);
}

double TESUncertainty::GetTESUncertainty(double pt, // MeV
					 double eta,
					 int ntracks,
					 TESComponent component)
{ 
  assert(component != REMAININGSYS && "User are not supposed to access REMAININGSYS component. Giving up");
  pt = pt / GeV;
  if(pt < 15)
    pt = 16.; // Take the lowest bin

  if(pt > 199)
    pt = 199.; // Take the highest bin

  if(fabs(eta)>2.5)
    {
      Warning("GetTESUncertainty",
	      "There is no TES uncertainty defined for |eta|>=2.5 (you gave %.2f). Returning 1.",
	      eta);
      return 1.;
    }

    
  // since it's an array - should be refactored
  int itrack = 0;
  if(ntracks > 1)
    itrack = 1;

  unsigned int iE = 0;
  for(iE = 0; iE < n_EtaBins; ++iE)
    if(fabs(eta) >= EtaBins[iE] && fabs(eta) < EtaBins[iE + 1])
      break;
  if(component == TOTAL && pt > 50.)
    return h1_TES_comps[FINAL][itrack][iE]->GetBinContent(h1_TES_comps[FINAL][itrack][iE]->FindBin(pt));
  if(component == INSITUSTAT)
    return getInSituStat(pt, ntracks);
  if(component == SYSREST)
    return getSystRest(pt, ntracks, itrack, iE);

  if(component == TOTAL){
    double closure = h1_TES_comps[CLOSURE][itrack][iE]->GetBinContent(h1_TES_comps[CLOSURE][itrack][iE]->FindBin(pt));
    double pu = h1_TES_comps[PU][itrack][iE]->GetBinContent(h1_TES_comps[PU][itrack][iE]->FindBin(pt));
    double insitustat = getInSituStat(pt, ntracks);
    double systrest = getSystRest(pt, ntracks, itrack, iE);
    return sqrt(pow(closure, 2) +
		pow(pu, 2) +
		pow(insitustat, 2) +
		pow(systrest, 2));
  }
  
  return h1_TES_comps[component][itrack][iE]->GetBinContent(h1_TES_comps[component][itrack][iE]->FindBin(pt));
}

double TESUncertainty::getInSituStat(const double& pt, const int& ntracks){
  double unc = ntracks == 1 ? m_dInSituStat1P : m_dInSituStat3P;
  return pt >= 50. ? 0. : unc;
}

double TESUncertainty::getSystRest(const double& pt, const int& ntracks, const int& itrack, const unsigned int& iE){ 
  if(pt >= 50.) // this should be a member - refactoring
    return h1_TES_comps[REMAININGSYS][itrack][iE]->GetBinContent(h1_TES_comps[REMAININGSYS][itrack][iE]->FindBin(pt));
  double insitusys = ntracks == 1 ? m_dInSituSyst1P : m_dInSituSyst3P;
  double remainingsyst = h1_TES_comps[REMAININGSYS][itrack][iE]->GetBinContent(h1_TES_comps[REMAININGSYS][itrack][iE]->FindBin(pt));
  return sqrt(pow(insitusys, 2) +
	      pow(remainingsyst, 2));
}

double TESUncertainty::interpolateLin(const double& pt, const double& value){
  assert(pt <= 70.);
  if(pt < 50.)
    return value;
  return (value * (1  - (pt - 50.) / 20.));
}

#endif
