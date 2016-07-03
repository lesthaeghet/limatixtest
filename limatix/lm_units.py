
# lm_units: A pure_python dg_units workalike

import sys
import re
import copy
import ast
import math

try: 
    import builtins  # python3
    pass
except ImportError: 
    import __builtin__ as builtins # python2
    pass

if not hasattr(builtins,"unicode"):
    unicode=str   # python3
    pass

UnitDict={} # of class Unit
NextUnitIndex=0
MeasDict={} # Dictionary by measurement name strings of measurement units
EquivList=[] # of class Equivalence


Basic_Units =  ( # ***!!! IMPORTANT: Change in parallel withcopy in lm_units.py
	    "measurement='mass'\n"
	    "units[mass,si,preferredpower=3]='gram','grams'\n"
	    "abbrev[grams]='g'\n"

	    "measurement='number'\n"
	    "units[number]='unitless','unitless'\n"
	    "abbrev[unitless]=''\n"
	    "units[number]='percent','percent'\n"
	    "abbrev[percent]='%'\n"

	    "measurement='energy'\n"
	    "units[energy,si]='Joule','Joules'\n"
	    "abbrev[Joules]='J'\n"

	    
	    "measurement='power'\n"
	    "units[power,si]='Watt','Watts'\n"
	    "abbrev[Watts]='W'\n"


	    "measurement='voltage'\n"
	    "units[voltage,si]='Volt','Volts'\n"
	    "abbrev[Volts]='V'\n"

	    "measurement='current'\n"
	    "units[current,si]='Amp', 'Amps'\n"
	    "abbrev[Amps]='A'\n"

	    "measurement='length'\n"
	    "units[length,si]='meter','meters'\n"
	    "abbrev[meters]='m'\n"
	    "units[length]='inch','inches'\n"
	    "abbrev[inches]='in'\n"
      "units[length]='mil','mils'\n"
      "abbrev[mils]='mil'\n"
	    "units[length,si]='pixel','pixels'\n"
	    "abbrev[pixels]='p'\n"	    

	    "measurement='time'\n"
	    "units[time,si]='second','seconds'\n"
	    "abbrev[seconds]='s'\n"

            "measurement='frequency'\n"
	    "units[frequency,si]='Hertz','Hertz'\n"
	    "abbrev[Hertz]='Hz'\n"

	    "measurement='velocity'\n"
	    "units[velocity,si]='meter/second','meters/second'\n"
	    "abbrev[meters/second]='m/s'\n"

	    "measurement='angle'\n"
	    "units[angle]='radian','radians'\n"
	    "abbrev[radians]='r'\n"
	    
	    "measurement='rotation rate'\n"
	    "units[rotation rate]='radian/second','radians/second'\n"
	    "abbrev[radians/second]='r/s'\n"
 
	    "measurement='acceleration'\n"
	    "units[acceleration,si]='meter/second^2','meters/second^2'\n"
	    "abbrev[meters/second^2]='m/s^2'\n"
	    "units[acceleration]='gee','gees'\n"
	    "abbrev[gees]='g'\n"


	    "measurement='force'\n"
	    "units[force,si]='Newton','Newtons'\n"
	    "abbrev[Newtons]='N'\n"
	    "units[force]='pound','pounds'\n"
	    "abbrev[pounds]='lb'\n"
	    "units[force]='ounce','ounces'\n"
	    "abbrev[ounces]='oz'\n"
	    

	    "measurement='pressure'\n"
	    "units[pressure,si]='Pascal','Pascals'\n"
	    "abbrev[Pascals]='Pa'\n"

	    "measurement='temperature'\n"
	    "units[temperature,si]='Kelvin','Kelvin'\n"
	    "abbrev[Kelvin]='K'\n"

            "measurement='arbitrary'\n"
            "units[arbitrary,si]='arbitrary','arbitrary'\n"
            "abbrev[arbitrary]='Arb'\n"


            "equivalence[meters]='inches/25.4e-3'\n" # Warning: counter-intuitive. Read this as "1 meter is equivalent to 1/25.4e-3 inch
            "equivalence[meters]='mils/25.4e-6'\n"
	    "equivalence[Newtons]='kg m/s^2'\n"
	    "equivalence[Newtons]='Pascals m^2'\n"
	    "equivalence[Newton-meters]='inch-pounds/0.112984829'\n"
	    "equivalence[Newton-meters]='inch-ounces/0.00706155181'\n"
	    "equivalence[Pascals]='N/m^2'\n"
	    "equivalence[Pascals]='kg/m/s^2'\n"
	    "equivalence[Joules]='N m'\n" 
	    "equivalence[Joules]='kg m^2/s^2'\n" 
	    "equivalence[Joules]='Volts Amps Seconds'\n"
	    "equivalence[Joules]='Watt Seconds'\n"
	    "equivalence[Watts]='J/s'\n"
	    "equivalence[Watts]='kg m^2/s^3'\n"
	    "equivalence[Watts]='V A'\n"
            "equivalence[Hz]='1/s'\n"
            "equivalence[s]='1/Hz'\n"
	    "equivalence[unitless]='percent*100.0'\n"
	    "equivalence[]='unitless'\n"
)




class SIPrefix(object):
    Prefix=None
    Abbrev=None
    Power=None

    def __init__(self,Prefix,Abbrev,Power):
        self.Prefix=Prefix
        self.Abbrev=Abbrev
        self.Power=int(Power)
        pass        
    pass

SIPrefixes=[
    SIPrefix("Yotta","Y",24),
    SIPrefix("Zetta", "Z", 21),
    SIPrefix("Exa", "E", 18),
    SIPrefix("Peta", "P", 15),
    SIPrefix("Tera", "T", 12),
    SIPrefix("Giga", "G", 9),
    SIPrefix("Mega", "M", 6),
    SIPrefix("kilo", "k", 3),
    SIPrefix("milli", "m", -3),
    SIPrefix("micro", "u", -6), 
    SIPrefix("nano", "n", -9), 
    SIPrefix("pico", "p", -12),
    SIPrefix("femto", "f", -15), 
    SIPrefix("atto", "a", -18),
    SIPrefix("zepto", "z", -21), 
    SIPrefix("yocto", "y", -24),
];

SIByName=dict([ (Prefix.Prefix,Prefix) for Prefix in SIPrefixes ])
SIByAbbrev=dict([ (Prefix.Abbrev,Prefix) for Prefix in SIPrefixes ])
SIByPower=dict([ (Prefix.Power,Prefix) for Prefix in SIPrefixes ])


class Equivalence:
    ToReplace=None  # class units
    ReplaceWith=None  # class units

    def __init__(self,**kwargs):
        for kwarg in kwargs:
            assert(hasattr(self,kwarg))
            setattr(self,kwarg,kwargs[kwarg])
            pass
        pass

    pass


    
class Unit(object):
    MeasName=None
    SingularName=None
    PluralName=None
    AbbrevList=None # list of abbreviation strings
    Index=None
    PreferredPower=None # Preferred power of 10, typically 0, but 3 for grams indicating usual use of kg
    SiPrefixFlag=None
    
    def __init__(self,**kwargs):
        self.AbbrevList=[]
        for kwarg in kwargs:
            assert(hasattr(self,kwarg))
            setattr(self,kwarg,kwargs[kwarg])
            pass
        pass




    pass


def CompareUnitFactor(FactorA,FactorB):
    # returns < 0 for A < B, 0 for A==B, > 0  for A > B, computed according to unit index # and
    # alphabetical order for unknown units */

    if FactorA.Unit is not None and FactorB.Unit is None:
        return -1

    if FactorB.Unit is not None and FactorA.Unit is None:
        return 1

    if FactorA.Unit is not None and FactorB.Unit is not None:
        if FactorA.Unit.Index < FactorB.Unit.Index:
            return -1
        if FactorA.Unit.Index == FactorB.Unit.Index:
            assert(FactorA.Unit is FactorB.Unit)
            return 0
        if FactorA.Unit.Index > FactorB.Unit.Index:
            return 1
        
        assert() # unreachable
        pass

    if FactorA.Unit is None and FactorB.Unit is None:
        if FactorA.NameOnly > FactorB.NameOnly:
            return 1
        elif FactorA.NameOnly==FactorB.NameOnly:
            return 0
        else:
            return -1
        pass
    assert() # unreachable
    pass


    
class UnitFactor(object):
    Unit=None  # Unit object, either this OR 
    NameOnly=None   # NameOnly should be not None. Nameonly used for unknown units
    Power=None   # e.g 1 for emters, 2 for meters^2, positive for numerator... COEFFICIENT WILL BE TAKEN TO THIS POWER TOO!
    Coefficient=None # Coeffcient of this units. When normalized will be 1.0, except if there is a PreferredPower in which case this will be 10^PreferredPower

    def __init__(self,**kwargs):
        self.AbbrevList=[]
        for kwarg in kwargs:
            assert(hasattr(self,kwarg))
            setattr(self,kwarg,kwargs[kwarg])
            pass
        pass

    # (in) equality operators determine
    # whether this pairs of units are convertible
    # (not exactly identical)
    
    def __lt__(self,other):
        return CompareUnitFactor(self,other) < 0

    def __gt__(self,other):
        return CompareUnitFactor(self,other) > 0

    def __eq__(self,other):
        return CompareUnitFactor(self,other)==0

    def __le__(self,other):
        return CompareUnitFactor(self,other) <= 0

    def __ge__(self,other):
        return CompareUnitFactor(self,other) >= 0
        
    def __ne__(self,other):
        return CompareUnitFactor(self,other)!=0

    
    pass

class units(object):
    Factors=None # list of class UnitFactor
    Coefficient=None # coefficient out int front
    def __init__(self,**kwargs):
        self.Factors=[]
        self.Coefficient=1.0
        for kwarg in kwargs:
            assert(hasattr(self,kwarg))
            setattr(self,kwarg,kwargs[kwarg])
            pass
        pass

    def __mul__(self,other):
        if not isinstance(other,units):
            retval=copy.deepcopy(self)
            retval.Coefficient*=other
            return retval

        retval=copy.deepcopy(self)

        accumulatemultiply(retval,other)
        
        return retval


    def __pow__(self,other):
        assert(not isinstance(other,units))

        
        retval=copy.deepcopy(self)

        for factor in retval.Factors:
            factor.Power *= other

            # Don't need to modify coefficient because power
            # implies on coefficient
            #factor.Coefficient = factor.Coefficient**other
            
            pass
        retval.Coefficient=retval.Coefficient ** other

        retval.sortunits()
        return retval

    def __div__(self,other):
        if not isinstance(other,units):
            retval=copy.deepcopy(self)
            retval.Coefficient/=other
            return retval

        retval=copy.deepcopy(self)

        accumulatedivide(retval,other)
        return retval

    def __str__(self):
        return printunits(self,True)

    def AddUnitFactor(self,FactorName):
        FactorName=FactorName.strip()

        GotUnit=None
        Coefficient=1.0
        
        if FactorName in UnitDict:
            GotUnit=UnitDict[FactorName]
            pass
        (SiPrefix,SiPrefixPower)=HasSIPrefix(FactorName)
        if GotUnit is None and SiPrefix is not None:
            TryFactorName=FactorName[len(SiPrefix):]
            if TryFactorName in UnitDict:
                GotUnit=UnitDict[TryFactorName]
                Coefficient=10**SiPrefixPower
                pass
            pass
        if GotUnit is not None:
            # Found unit structure
            Factor=UnitFactor(Unit=GotUnit,Power=1.0,Coefficient=Coefficient)
            pass
        else:
            Factor=UnitFactor(NameOnly=FactorName,Power=1.0,Coefficient=Coefficient)
            pass
        self.Factors.append(Factor)
        pass

    def sortunits(self):
        # !!! in place !!!
        
        # Pull out all coefficients out in front
        for Factor in self.Factors:
            self.Coefficient *= pow(Factor.Coefficient,Factor.Power)
            Factor.Coefficient=1.0

            pass
        # perform sort
        self.Factors.sort()

        # Combine like units!

        pos=0
        while pos < len(self.Factors)-1:
            if self.Factors[pos]==self.Factors[pos+1]:
                self.Factors[pos].Power += self.Factors[pos+1].Power
                del self.Factors[pos+1]

                if abs(self.Factors[pos].Power) < 1e-8:
                    # units canceled!
                    del self.Factors[pos]
                    pass
                pass
            else:
                pos+=1
            pass
        # "normalize" coefficients (make everything use the preferred power)  

        for Factor in self.Factors:
            if Factor.Unit is not None and Factor.Unit.PreferredPower != 0:
                Factor.Coefficient = 10**Factor.Unit.PreferredPower
                self.Coefficient /= Factor.Coefficient**Factor.Power
                pass
            pass

        # Resort according to power: 
        # Powers of 1.0 go first, followed by powers > 1.0 in increasing order, followed by powers < 1.0 in decreasing order
        self.Factors.sort(key = lambda Factor: Factor.Power)
        pass 
    
    
    pass


# Parsing code follows dg_units syntax (see dg_units.syn)

def parseunits_right(unitstr):
    (remaining,unitpower)=parseunitpower_right(unitstr)

    if remaining.endswith('*'):
        (remaining2,unitsobj)=parseunits_right(remaining[:-1].strip())
        return (remaining2,unitsobj*unitpower)
    elif remaining.endswith('-'):
        (remaining2,unitsobj)=parseunits_right(remaining[:-1].strip())
        return (remaining2,unitsobj*unitpower)
    elif remaining.endswith('/'):
        (remaining2,unitsobj)=parseunits_right(remaining[:-1].strip())
        return (remaining2,unitsobj/unitpower)
    elif len(remaining) > 0:
        (remaining2,unitsobj)=parseunits_right(remaining[:-1].strip())
        return (remaining2,unitsobj*unitpower)
    return (remaining,unitpower)


findpower_right=re.compile(r"""(.*?)(\^)((?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)$""")
findfloat_right=re.compile(r"""(.*?)((?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)$""")
findunitname_right=re.compile(r"""(.*?)([a-zA-Z]+)$""")
                              
def parseunitpower_right(unitstr):
    power=1.0

    # parse ^real number on r.h.s
    matchobj=findpower_right.match(unitstr)
    if matchobj is not None:
        power=float(matchobj.group(3))
        unitstr=matchobj.group(1)   # remaining portion of unit factor
        pass
    
    if unitstr.endswith(')'):
        # parentheses
        (remaining,unitsobj)=parseunits_right(unitstr[:-1])

        if remaining[-1] != '(':
            raise ValueError("Mismatched Parentheses in %s" % (unitstr))
        remaining=remaining[:-1].strip()
        pass

    unitsobj=None
    
    # Try to match a coefficient
    matchobj=findfloat_right.match(unitstr)
    if matchobj is not None:
        remaining=matchobj.group(1).strip()
        coefficient=float(matchobj.group(2))
        unitsobj=units()*coefficient
        pass
    
    # Try to match a unit name
    matchobj=findunitname_right.match(unitstr)
    if matchobj is not None:
        remaining=matchobj.group(1).strip()
        unitname=matchobj.group(2)
        unitsobj=units()
        unitsobj.AddUnitFactor(unitname)
        pass
    
    if unitsobj is None:
        raise ValueError("Parse error on R.H.S of %s" % (unitstr))

    if power != 1.0:
        unitsobj=unitsobj**power
        pass

    return (remaining,unitsobj)

# Try to match 
def parseunits(unitstr):

    if unitstr is None:
        return units()

    if unitstr.strip()=="":
        return units()
    
    (remaining,unitsobj)=parseunits_right(unitstr.strip())
    assert(len(remaining)==0)

    unitsobj.sortunits()
    
    return unitsobj
    

def units_config(configstring):

    # we don't support multi-line initialization commands


    global NextUnitIndex
    
    # Split commands by line
    initialization_commands=configstring.split("\n")

    # Strip whitespace
    initcommands=[ initcommand.strip() for initcommand in initialization_commands ]

    for initcommand in initcommands:

        if initcommand=="insert_basic_units":
            units_config(Basic_Units)
            pass
        elif initcommand.startswith("measurement"):
            equals_string=initcommand[11:].strip()
            if equals_string[0] != '=':
                raise ValueError("Error parsing measurement \"%s\": missing equals" % (initcommand))
            quoted_string=equals_string[1:]
            meas_str=unicode(ast.literal_eval(quoted_string))
            if meas_str not in MeasDict:
                MeasDict[meas_str]=[]
                pass
            
            pass
        elif initcommand.startswith("units"):
            # define units for a measurement
            matchobj=re.match(r"""units\[([^]]+)\]=(.*)""",initcommand)
            if matchobj is None:
                raise ValueError("Parse error in units line %s" % (initcommand))
            measurement_comma_params=matchobj.group(1)
            valueliststr='['+matchobj.group(2)+']'
            valuelist=list(ast.literal_eval(valueliststr))

            siflag=False
            preferredpower=0.0
            
            measurement_params=measurement_comma_params.split(',')
            measurement=measurement_params[0].strip()
            for param in measurement_params[1:]:
                if param.strip()=="si":
                    siflag=True
                    pass
                elif param.startswith("preferredpower="):
                    preferredpower=float(param[15:])
                    pass
                else:
                    raise ValueError("units_config(): Unknown unit parameter %s" % (param))
                pass

            UnitObj=Unit(MeasName=measurement,SingularName=valuelist[0],PluralName=valuelist[1],SiPrefixFlag=siflag,PreferredPower=preferredpower,Index=NextUnitIndex)
            NextUnitIndex+=1
            UnitDict[valuelist[0]]=UnitObj
            UnitDict[valuelist[1]]=UnitObj
            
            MeasDict[measurement].append(UnitObj)
            
            
            
            pass

        elif initcommand.startswith("abbrev"):
            matchobj=re.match(r"""abbrev\[([^]]+)\]=(.*)""",initcommand)
            if matchobj is None:
                raise ValueError("Error parsing abbreviation \"%s\"" % (initcommand))
            FullUnitName=matchobj.group(1)
            AbbreviatedName=unicode(ast.literal_eval(matchobj.group(2)))

            if FullUnitName not in UnitDict:
                raise ValueError("Abbreviation for unknown unit in \"%s\"" % (initcommand))
            UnitDict[FullUnitName].AbbrevList.append(AbbreviatedName)
            if AbbreviatedName not in UnitDict: 
                UnitDict[AbbreviatedName]=UnitDict[FullUnitName]
                pass
            pass

        elif initcommand.startswith("equivalence"):
            # Equivalence not yet implemented
            pass
        elif initcommand=='':
            # blank line
            pass
        else:
            raise ValueError("Unknown initcommand: \"%s\"" % (initcommand))
        pass
    pass

def multiplyunits(comba,combb):
    return comba*combb

def divideunits(comba,combb):
    return comba/combb

def powerunits(comba,power):
    return comba**power

def accumulatemultiply(comba,combb):
    comba.Factors.extend(copy.deepcopy(combb.Factors))
    comba.Coefficient*=combb.Coefficient
    
    comba.sortunits() # sort and combine like units
    return comba

def accumulatedivide(comba,combb):
    
    # Move additional factors to denominator
    additionalfactors=copy.deepcopy(combb.Factors)
    for factor in additionalfactors:
        factor.Power=-factor.Power
        pass
        
    comba.Factors.extend(additionalfactors)
    comba.Coefficient/=combb.Coefficient
    
    comba.sortunits() # sort and combine like units

    return comba


def accumulatemultiplystr(comba,combb):
    return accumulatemultiply(comba,parseunits(combb))

def accumulatedividestr(comba,combb):
    return accumulatedivide(comba,parseunits(combb))

def simplifyunits(comba):
    # Not fully implemented
    comba.sortunits()
    return comba

def extractcoefficient(comb):

    # factor multiplicative coefficient out in front, modifying unit structure passed to this call

  Coefficient=comb.Coefficient
  comb.Coefficient=1.0
  
  return Coefficient;

def copyunits(comb):
    return copy.deepcopy(comb)


def comparerawunits(CombA,CombB):
    # returns 0 for non-equal, When the unit combinations are equivalent, the coefficient of CombA relative
    #  to CombB is returned. 
    # CombA and CombB MUST be already sorted sith wortunits() method

    if len(CombA.Factors) != len(CombB.Factors):
        return 0.0

    for Pos in range(len(CombA.Factors)):
        FactorA=CombA.Factors[Pos]
        FactorB=CombB.Factors[Pos]

        if FactorA != FactorB:
            return 0.0
        else:
            if FactorA.Power != FactorB.Power:
                return 0.0
            assert(FactorA.Coefficient==FactorB.Coeffcient) # Should always match because of normalization in sorting function
            pass
        pass

    return CombA.Coefficient/CombB.Coefficient



def compareunits(comba,combb):

    ca_copy=copy.deepcopy(comba)
    cb_copy=copy.deepcopy(combb)

    simplifyunits(ca_copy)
    simplifyunits(cb_copy)

    return comparerawunits(ca_copy,cb_copy)


    
def convertunits(old,new):
    # returns coefficient by which to multiply old value, or 0.0 if units are incompatible
    return compareunits(old,new)



def FactorName(Factor,longflag,pluralflag):

    if Factor.Unit is not None:
        if not longflag:
            if len(Factor.Unit.AbbrevList) > 0:
                Abbrev=Factor.Unit.AbbrevList[0]
                return Abbrev
            pass
        if pluralflag:
            return Factor.Unit.PluralName
        return Factor.Unit.SingularName
    else:
        return Factor.NameOnly
    pass

            
            
def HasSIPrefix(Name):
    # look up unabbreviated prefixes, case insensitive
    for SiPrefix in SIPrefixes:
        if Name.upper().startswith(SiPrefix.Prefix.upper()):
            return (SiPrefix.Prefix,SiPrefix.Power)
        pass

    # look up abbreviated prefixes, case sensitive
    for SiPrefix in SIPrefixes:
        if Name.startswith(SiPrefix.Abbrev):
            return (SiPrefix.Abbrev,SiPrefix.Power)
        pass
    
    return (None,0)

def IsSiPrefix(Power,longflag):
    # return SI prefix string for power \approx Power, or None
    if abs(Power) < 1e-8:
        return ""

    for SiPrefix in SIPrefixes:
        if abs(SiPrefix.Power-Power) < 1e-8:
            if longflag or SiPrefix.Abbrev is None:
                return SiPrefix.Prefix
            else:
                return SiPrefix.Abbrev
            pass
        pass
    return None

    
    


def printunits(Comb,longflag=False):

    first=True
    lastpower=0
    Coefficient=1.0
    hasdenominator=False
    buff=""
    
    for Factor in Comb.Factors:
        if Factor.Power > 0:
            if lastpower > 0:
                # factors separated by *
                buff+="*"
                pass
            lastpower=Factor.Power

            if first:
                # Write SI prefix for unit combination

                # Just this first Factor
                FactorPrefix=IsSiPrefix(math.log10(Factor.Coefficient),False)
                FactorPlusCombPrefix=IsSiPrefix(math.log10(Comb.Coefficient**(1.0/Factor.Power)*Factor.Coefficient),longflag)
                if Factor.Unit is not None and Factor.Unit.SiPrefixFlag and FactorPrefix is not None and FactorPlusCombPrefix is not None:
                    # Print combined prefix
                    buff+=FactorPlusCombPrefix
                    pass
                else:
                    # accumulate Comb coefficient and print out regular prefix for factor
                    Coefficient *= Comb.Coefficient

                    FactorPrefix=IsSiPrefix(math.log10(Factor.Coefficient),longflag)
                    if Factor.Unit is not None and Factor.Unit.SiPrefixFlag and FactorPrefix is not None:
                        buff+=FactorPrefix
                        pass
                    else:
                        # Couldn't print SI prefix for Factor. Accumulate coefficient to print at end 

                        Coefficient *= Factor.Coefficient**Factor.Power
                        pass
                    pass
                first=0
                pass
            else:
                # Not first
                if abs(Factor.Coefficient-1.0) > 1e-8:
                    FactorPrefix=IsSiPrefix(math.log10(Factor.Coefficient),longflag)
                    if FactorPrefix is not None:
                        buff+=FactorPrefix
                        pass
                    else:
                        # Couldn't print SI prefix for Factor. Accumulate coefficient to print at end                         
                        Coefficient *=Factor.Coefficient**Factor.Power
                        pass
                    pass
                pass
            buff+=FactorName(Factor,longflag,True)
            if abs(Factor.Power-1.0) > 1e-8:
                buff+="^%.6g" % (Factor.Power)
                pass
            
            
            pass
        else:
            # not (Factor.Power > 0):
            hasdenominator=True
            pass
        pass

    if first:
        # Never wrote a factor in the numerator
        # accumulabte Comb coefficient
        Coefficient *= Comb.Coefficient
        first=0

        if hasdenominator:
            # write 1 in numerator:
            buff+="1"
            pass
        pass


    # print denominator
    
    for Factor in Comb.Factors:
        if Factor.Power < 0:
            buff+="/"  # slash to pad divsors

            # attempt to write si prefix
            if abs(Factor.Coefficient-1.0) > 1e-8:
                FactorPrefix=IsSiPrefix(math.log10(Factor.Coefficient),longflag)
                if Factor.Unit is not None and Factor.Unit.SiPrefixFlag and FactorPrefix is not None:
                    buff+=FactorPrefix
                    pass
                else:
                    Coefficient *= Factor.Coefficient**Factor.Power
                    pass
                pass
            
            buff+=FactorName(Factor,longflag,False)

            # Print factor power
            if abs(Factor.Power+1.0) > 1e-8:
                buff+="^%.6g" % (-Factor.Power)
                pass
            
            pass
        pass

    # print accumulated coefficient, if any
    if abs(Coefficient-1.0) > 1e-8:
        buff+="*%.6e" % (Coefficient)
        pass

    return buff


# dg_units compatibility
dgu_units  = units

#import pdb
#pdb.set_trace()
#foo=parseunits('m^2/s')

units_config("insert_basic_units") # Always include the basic units for now
